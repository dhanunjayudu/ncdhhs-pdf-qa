import os
import json
import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import tempfile
import aiofiles
import hashlib
import uuid

import boto3
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
import requests
from bs4 import BeautifulSoup
import pypdf
from urllib.parse import urljoin, urlparse
import numpy as np
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="NC DHHS PDF Q&A API",
    description="API for processing PDF documents and answering questions using AWS Bedrock and OpenSearch",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# AWS Configuration
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
AWS_PROFILE = os.getenv("AWS_PROFILE", None)
OPENSEARCH_ENDPOINT = os.getenv("OPENSEARCH_ENDPOINT", "")
OPENSEARCH_INDEX = os.getenv("OPENSEARCH_INDEX", "ncdhhs-documents")

# Initialize AWS clients
# Use profile only if specified, otherwise use default credentials (IAM role in ECS)
if AWS_PROFILE:
    session = boto3.Session(profile_name=AWS_PROFILE)
    bedrock_runtime = session.client("bedrock-runtime", region_name=AWS_REGION)
    s3_client = session.client("s3", region_name=AWS_REGION)
else:
    # Use default credentials (IAM role in ECS)
    bedrock_runtime = boto3.client("bedrock-runtime", region_name=AWS_REGION)
    s3_client = boto3.client("s3", region_name=AWS_REGION)

# Initialize OpenSearch client
if OPENSEARCH_ENDPOINT:
    if AWS_PROFILE:
        # Use session credentials when profile is specified
        credentials = session.get_credentials()
    else:
        # Use default credentials (IAM role in ECS)
        credentials = boto3.Session().get_credentials()
    
    awsauth = AWS4Auth(
        credentials.access_key,
        credentials.secret_key,
        AWS_REGION,
        'es',
        session_token=credentials.token
    )

    opensearch_client = OpenSearch(
        hosts=[{'host': OPENSEARCH_ENDPOINT.replace('https://', ''), 'port': 443}],
        http_auth=awsauth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        timeout=60
    )
else:
    opensearch_client = None

# Pydantic models
class PDFLink(BaseModel):
    title: str
    url: HttpUrl
    id: Optional[str] = None

class ExtractLinksRequest(BaseModel):
    url: HttpUrl

class ProcessPDFBatchRequest(BaseModel):
    pdf_links: List[PDFLink]

class CreateKnowledgeBaseRequest(BaseModel):
    documents: List[Dict[str, Any]]

class AskQuestionRequest(BaseModel):
    question: str

class ProcessedDocument(BaseModel):
    title: str
    url: str
    content: str
    pages: int
    processedAt: str
    success: bool = True

# OpenSearch operations
async def initialize_opensearch_index():
    """Initialize OpenSearch index with proper mapping for vector search"""
    if not opensearch_client:
        logger.warning("OpenSearch client not initialized - using fallback storage")
        return False
    
    try:
        # Check if index exists
        if opensearch_client.indices.exists(index=OPENSEARCH_INDEX):
            logger.info(f"OpenSearch index '{OPENSEARCH_INDEX}' already exists")
            return True
        
        # Create index with vector field mapping
        index_mapping = {
            "settings": {
                "index": {
                    "number_of_shards": 1,
                    "number_of_replicas": 0,
                    "knn": True,
                    "knn.algo_param.ef_search": 100
                }
            },
            "mappings": {
                "properties": {
                    "document_id": {"type": "keyword"},
                    "title": {"type": "text"},
                    "url": {"type": "keyword"},
                    "content": {"type": "text"},
                    "chunk_text": {"type": "text"},
                    "chunk_index": {"type": "integer"},
                    "pages": {"type": "integer"},
                    "processed_at": {"type": "date"},
                    "embedding": {
                        "type": "knn_vector",
                        "dimension": 1024,
                        "method": {
                            "name": "hnsw",
                            "space_type": "cosinesimil",
                            "engine": "nmslib",
                            "parameters": {
                                "ef_construction": 128,
                                "m": 24
                            }
                        }
                    }
                }
            }
        }
        
        response = opensearch_client.indices.create(
            index=OPENSEARCH_INDEX,
            body=index_mapping
        )
        
        logger.info(f"Created OpenSearch index '{OPENSEARCH_INDEX}': {response}")
        return True
        
    except Exception as e:
        logger.error(f"Error initializing OpenSearch index: {str(e)}")
        return False

async def store_document_chunks_in_opensearch(document: Dict[str, Any], chunks: List[str], embeddings: List[List[float]]):
    """Store document chunks and embeddings in OpenSearch"""
    if not opensearch_client:
        logger.warning("OpenSearch not available - skipping storage")
        return False
    
    try:
        # Ensure index exists before storing
        if not opensearch_client.indices.exists(index=OPENSEARCH_INDEX):
            logger.warning(f"Index {OPENSEARCH_INDEX} does not exist, creating it...")
            await initialize_opensearch_index()
        
        document_id = hashlib.md5(document['url'].encode()).hexdigest()
        
        # Prepare bulk operations
        bulk_operations = []
        
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            doc_data = {
                "document_id": document_id,
                "title": document['title'],
                "url": document['url'],
                "content": document['content'],
                "chunk_text": chunk,
                "chunk_index": i,
                "pages": document['pages'],
                "processed_at": document['processedAt'],
                "embedding": embedding
            }
            
            # Add index operation
            bulk_operations.append({
                "index": {
                    "_index": OPENSEARCH_INDEX,
                    "_id": f"{document_id}_{i}"
                }
            })
            bulk_operations.append(doc_data)
        
        # Execute bulk operation
        if bulk_operations:
            response = opensearch_client.bulk(body=bulk_operations)
            
            if response.get('errors'):
                logger.error(f"Bulk indexing errors: {response}")
                return False
            
            logger.info(f"Stored {len(chunks)} chunks for document '{document['title']}'")
            return True
            
    except Exception as e:
        logger.error(f"Error storing document in OpenSearch: {str(e)}")
        return False

async def search_similar_chunks(query_embedding: List[float], k: int = 5) -> List[Dict[str, Any]]:
    """Search for similar document chunks using vector similarity"""
    if not opensearch_client:
        logger.warning("OpenSearch not available - returning empty results")
        return []
    
    try:
        search_query = {
            "size": k,
            "query": {
                "knn": {
                    "embedding": {
                        "vector": query_embedding,
                        "k": k
                    }
                }
            },
            "_source": ["title", "url", "chunk_text", "chunk_index", "pages"]
        }
        
        response = opensearch_client.search(
            index=OPENSEARCH_INDEX,
            body=search_query
        )
        
        results = []
        for hit in response['hits']['hits']:
            results.append({
                "title": hit['_source']['title'],
                "url": hit['_source']['url'],
                "chunk_text": hit['_source']['chunk_text'],
                "chunk_index": hit['_source']['chunk_index'],
                "pages": hit['_source']['pages'],
                "score": hit['_score']
            })
        
        return results
        
    except Exception as e:
        logger.error(f"Error searching OpenSearch: {str(e)}")
        return []

async def get_all_documents_from_opensearch() -> List[Dict[str, Any]]:
    """Get all unique documents from OpenSearch"""
    if not opensearch_client:
        return []
    
    try:
        # Check if index exists, create if it doesn't
        if not opensearch_client.indices.exists(index=OPENSEARCH_INDEX):
            logger.warning(f"Index {OPENSEARCH_INDEX} does not exist, creating it...")
            await initialize_opensearch_index()
            return []  # Return empty list after creating index
        
        # Get unique documents by aggregating on document_id
        search_query = {
            "size": 0,
            "aggs": {
                "unique_documents": {
                    "terms": {
                        "field": "document_id",
                        "size": 1000
                    },
                    "aggs": {
                        "document_info": {
                            "top_hits": {
                                "size": 1,
                                "_source": ["title", "url", "content", "pages", "processed_at"]
                            }
                        }
                    }
                }
            }
        }
        
        response = opensearch_client.search(
            index=OPENSEARCH_INDEX,
            body=search_query
        )
        
        documents = []
        for bucket in response['aggregations']['unique_documents']['buckets']:
            doc_hit = bucket['document_info']['hits']['hits'][0]['_source']
            documents.append({
                "title": doc_hit['title'],
                "url": doc_hit['url'],
                "content": doc_hit['content'],
                "pages": doc_hit['pages'],
                "processedAt": doc_hit['processed_at'],
                "success": True
            })
        
        return documents
        
    except Exception as e:
        logger.error(f"Error getting documents from OpenSearch: {str(e)}")
        # If index doesn't exist, try to create it
        if "index_not_found_exception" in str(e):
            logger.warning("Index not found, attempting to create it...")
            try:
                await initialize_opensearch_index()
                return []  # Return empty list after creating index
            except Exception as create_error:
                logger.error(f"Failed to create index: {str(create_error)}")
        return []

# Helper functions
async def extract_pdf_links_from_website(url: str) -> List[PDFLink]:
    """Extract PDF links from a website"""
    try:
        logger.info(f"Extracting PDF links from: {url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        pdf_links = []
        
        # Find PDF links in href attributes
        for link in soup.find_all('a', href=True):
            href = link['href']
            if href.lower().endswith('.pdf'):
                full_url = urljoin(url, href)
                title = link.get_text(strip=True) or f"PDF Document {len(pdf_links) + 1}"
                pdf_links.append(PDFLink(title=title, url=full_url))
        
        logger.info(f"Found {len(pdf_links)} PDF links")
        return pdf_links
        
    except Exception as e:
        logger.error(f"Error extracting PDF links: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to extract PDF links: {str(e)}")

async def download_and_extract_pdf_text(url: str, timeout: int = 180) -> str:
    """Download PDF and extract text content"""
    try:
        logger.info(f"Downloading PDF from: {url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=timeout, stream=True)
        response.raise_for_status()
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            for chunk in response.iter_content(chunk_size=8192):
                temp_file.write(chunk)
            temp_file_path = temp_file.name
        
        try:
            # Extract text using pypdf
            with open(temp_file_path, 'rb') as file:
                pdf_reader = pypdf.PdfReader(file)
                text_content = ""
                
                for page_num, page in enumerate(pdf_reader.pages):
                    try:
                        page_text = page.extract_text()
                        if page_text.strip():
                            text_content += f"\n--- Page {page_num + 1} ---\n{page_text}\n"
                    except Exception as e:
                        logger.warning(f"Error extracting text from page {page_num + 1}: {str(e)}")
                        continue
                
                if not text_content.strip():
                    raise ValueError("No text content extracted from PDF")
                
                logger.info(f"Successfully extracted {len(text_content)} characters from PDF")
                return text_content.strip()
                
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_file_path)
            except:
                pass
                
    except requests.exceptions.Timeout:
        logger.error(f"Timeout downloading PDF from {url}")
        raise HTTPException(status_code=408, detail=f"Timeout downloading PDF from {url}")
    except Exception as e:
        logger.error(f"Error processing PDF from {url}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to process PDF: {str(e)}")

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """Split text into overlapping chunks"""
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        # Try to break at sentence boundary
        if end < len(text):
            # Look for sentence endings within the last 200 characters
            last_period = text.rfind('.', start, end)
            last_exclamation = text.rfind('!', start, end)
            last_question = text.rfind('?', start, end)
            
            sentence_end = max(last_period, last_exclamation, last_question)
            
            if sentence_end > start + chunk_size - 200:
                end = sentence_end + 1
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        # Move start position with overlap
        start = end - overlap
        if start >= len(text):
            break
    
    return chunks

async def create_embedding(text: str) -> List[float]:
    """Create embedding using AWS Bedrock Titan"""
    try:
        # Truncate text if too long (Titan has limits)
        max_length = 8000
        if len(text) > max_length:
            text = text[:max_length]
        
        body = json.dumps({
            "inputText": text,
            "dimensions": 1024,
            "normalize": True
        })
        
        response = bedrock_runtime.invoke_model(
            modelId="amazon.titan-embed-text-v2:0",
            body=body
        )
        
        response_body = json.loads(response.get('body').read())
        embedding = response_body.get('embedding')
        
        if not embedding:
            raise ValueError("No embedding returned from Bedrock")
        
        return embedding
        
    except Exception as e:
        logger.error(f"Error creating embedding: {str(e)}")
        # Return zero vector as fallback
        return [0.0] * 1024  # Titan v2 embedding dimension

async def query_bedrock(question: str, context: str) -> str:
    """Query AWS Bedrock for answer"""
    try:
        prompt = f"""Human: Based on the following context from NC DHHS Child Welfare documents, please answer the question. If the answer is not in the context, say "I don't have enough information to answer that question based on the provided documents."

Context:
{context}

Question: {question}

Please provide a comprehensive answer based on the context provided."""

        body = json.dumps({
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": 1000,
            "temperature": 0.1,
            "top_p": 0.9,
            "anthropic_version": "bedrock-2023-05-31"
        })
        
        try:
            # Try Claude 3.5 Sonnet first (latest available)
            response = bedrock_runtime.invoke_model(
                modelId="anthropic.claude-3-5-sonnet-20240620-v1:0",
                body=body
            )
        except Exception as claude_error:
            logger.warning(f"Claude 3.5 Sonnet failed, trying Nova Pro: {str(claude_error)}")
            try:
                # Try Amazon Nova Pro as fallback
                nova_body = json.dumps({
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 1000,
                    "temperature": 0.1,
                    "top_p": 0.9
                })
                response = bedrock_runtime.invoke_model(
                    modelId="amazon.nova-pro-v1:0",
                    body=nova_body
                )
            except Exception as nova_error:
                logger.warning(f"Nova Pro failed, trying Titan: {str(nova_error)}")
                # Final fallback to Titan Text
                titan_body = json.dumps({
                    "inputText": prompt,
                    "textGenerationConfig": {
                        "maxTokenCount": 1000,
                        "temperature": 0.1,
                        "topP": 0.9
                    }
                })
                response = bedrock_runtime.invoke_model(
                    modelId="amazon.titan-text-express-v1",
                    body=titan_body
                )
        
        response_body = json.loads(response['body'].read())
        
        # Handle different response formats
        if 'content' in response_body:
            # Claude response format
            return response_body['content'][0]['text']
        elif 'message' in response_body:
            # Nova response format
            return response_body['message']['content'][0]['text']
        elif 'results' in response_body:
            # Titan response format
            return response_body['results'][0]['outputText']
        else:
            return "I apologize, but I encountered an issue processing your question."
            
    except Exception as e:
        logger.error(f"Error querying Bedrock: {str(e)}")
        return "I apologize, but I encountered an error while processing your question. Please try again."

# API Routes
@app.on_event("startup")
async def startup_event():
    """Initialize OpenSearch index on startup"""
    await initialize_opensearch_index()

@app.get("/")
async def root():
    return {"message": "NC DHHS PDF Q&A API with OpenSearch Vector Database", "status": "running"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    documents = await get_all_documents_from_opensearch()
    return {
        "status": "healthy",
        "documents_count": len(documents),
        "opensearch_available": opensearch_client is not None,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/extract-pdf-links")
async def extract_pdf_links(request: ExtractLinksRequest):
    """Extract PDF links from a website"""
    pdf_links = await extract_pdf_links_from_website(str(request.url))
    return {"pdf_links": pdf_links}

@app.post("/process-pdf-batch")
async def process_pdf_batch(request: ProcessPDFBatchRequest, background_tasks: BackgroundTasks):
    """Process multiple PDFs and store in vector database"""
    results = []
    
    for pdf_link in request.pdf_links:
        try:
            logger.info(f"Processing PDF: {pdf_link.title}")
            
            # Download and extract text
            content = await download_and_extract_pdf_text(str(pdf_link.url))
            
            # Count pages (rough estimate)
            pages = content.count("--- Page") if "--- Page" in content else 1
            
            # Create document object
            document = {
                "title": pdf_link.title,
                "url": str(pdf_link.url),
                "content": content,
                "pages": pages,
                "processedAt": datetime.now().isoformat(),
                "success": True
            }
            
            # Process in background
            background_tasks.add_task(process_document_for_vector_search, document)
            
            results.append(ProcessedDocument(**document))
            
        except Exception as e:
            logger.error(f"Error processing PDF {pdf_link.title}: {str(e)}")
            error_doc = ProcessedDocument(
                title=pdf_link.title,
                url=str(pdf_link.url),
                content="",
                pages=0,
                processedAt=datetime.now().isoformat(),
                success=False
            )
            results.append(error_doc)
    
    return {"processed_documents": results}

async def process_document_for_vector_search(document: Dict[str, Any]):
    """Process document for vector search storage"""
    try:
        # Chunk the document
        chunks = chunk_text(document['content'])
        
        # Create embeddings for each chunk
        embeddings = []
        for chunk in chunks:
            embedding = await create_embedding(chunk)
            embeddings.append(embedding)
        
        # Store in OpenSearch
        await store_document_chunks_in_opensearch(document, chunks, embeddings)
        
        logger.info(f"Successfully processed document '{document['title']}' with {len(chunks)} chunks")
        
    except Exception as e:
        logger.error(f"Error processing document for vector search: {str(e)}")

@app.get("/documents")
async def get_documents():
    """Get all processed documents"""
    documents = await get_all_documents_from_opensearch()
    return {"documents": documents}

@app.post("/ask")
async def ask_question(request: AskQuestionRequest):
    """Ask a question about the processed documents"""
    try:
        logger.info(f"Processing question: {request.question}")
        
        # Create embedding for the question
        question_embedding = await create_embedding(request.question)
        
        # Search for similar chunks
        similar_chunks = await search_similar_chunks(question_embedding, k=5)
        
        if not similar_chunks:
            return {
                "question": request.question,
                "answer": "I don't have any documents to search through. Please process some documents first.",
                "sources": []
            }
        
        # Prepare context from similar chunks
        context_parts = []
        sources = []
        
        for chunk in similar_chunks:
            context_parts.append(f"From '{chunk['title']}' (Page {chunk.get('pages', 'Unknown')}):\n{chunk['chunk_text']}")
            sources.append({
                "title": chunk['title'],
                "url": chunk['url'],
                "pages": chunk.get('pages', 'Unknown'),
                "relevance_score": chunk['score']
            })
        
        context = "\n\n".join(context_parts)
        
        # Get answer from Bedrock
        answer = await query_bedrock(request.question, context)
        
        return {
            "question": request.question,
            "answer": answer,
            "sources": sources
        }
        
    except Exception as e:
        logger.error(f"Error processing question: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing question: {str(e)}")

@app.delete("/documents")
async def clear_documents():
    """Clear all documents from the vector database"""
    try:
        if opensearch_client and opensearch_client.indices.exists(index=OPENSEARCH_INDEX):
            opensearch_client.indices.delete(index=OPENSEARCH_INDEX)
            await initialize_opensearch_index()
            logger.info("Cleared all documents from OpenSearch")
        
        return {"message": "All documents cleared successfully"}
        
    except Exception as e:
        logger.error(f"Error clearing documents: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error clearing documents: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
