import os
import json
import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import tempfile
import aiofiles

import boto3
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
import requests
from bs4 import BeautifulSoup
import pypdf
from urllib.parse import urljoin, urlparse
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="NC DHHS PDF Q&A API",
    description="API for processing PDF documents and answering questions using AWS Bedrock",
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
AWS_PROFILE = os.getenv("AWS_PROFILE")

# Initialize AWS clients
# Use profile only if specified (for local development), otherwise use default credentials (for ECS)
if AWS_PROFILE:
    session = boto3.Session(profile_name=AWS_PROFILE)
else:
    session = boto3.Session()

bedrock_runtime = session.client("bedrock-runtime", region_name=AWS_REGION)
s3_client = session.client("s3", region_name=AWS_REGION)

# Global storage (in production, use a proper database)
document_store: List[Dict[str, Any]] = []
embeddings_store: List[Dict[str, Any]] = []

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
            href = link.get('href')
            if href and href.lower().endswith('.pdf'):
                title = link.get_text(strip=True) or link.get('title', f'Document {len(pdf_links) + 1}')
                full_url = urljoin(url, href)
                pdf_links.append(PDFLink(
                    title=title,
                    url=full_url,
                    id=f"pdf_{len(pdf_links)}"
                ))
        
        # Find PDF links in data attributes (for dynamic content)
        for element in soup.find_all(attrs={"data-download-url": True}):
            download_url = element.get('data-download-url')
            if download_url and download_url.lower().endswith('.pdf'):
                title = element.get('data-title') or element.get_text(strip=True) or f'Document {len(pdf_links) + 1}'
                full_url = urljoin(url, download_url)
                pdf_links.append(PDFLink(
                    title=title,
                    url=full_url,
                    id=f"pdf_{len(pdf_links)}"
                ))
        
        logger.info(f"Found {len(pdf_links)} PDF links")
        return pdf_links
        
    except Exception as e:
        logger.error(f"Error extracting PDF links: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to extract PDF links: {str(e)}")

async def download_and_process_pdf(pdf_link: PDFLink) -> Optional[ProcessedDocument]:
    """Download and process a single PDF"""
    try:
        logger.info(f"Processing PDF: {pdf_link.title}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        # Download PDF
        response = requests.get(str(pdf_link.url), headers=headers, timeout=60)
        response.raise_for_status()
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            temp_file.write(response.content)
            temp_file_path = temp_file.name
        
        try:
            # Extract text from PDF
            with open(temp_file_path, 'rb') as file:
                pdf_reader = pypdf.PdfReader(file)
                text_content = ""
                
                for page_num, page in enumerate(pdf_reader.pages):
                    try:
                        text_content += page.extract_text() + "\n"
                    except Exception as e:
                        logger.warning(f"Error extracting text from page {page_num + 1}: {str(e)}")
                        continue
                
                num_pages = len(pdf_reader.pages)
            
            # Clean up text
            text_content = text_content.strip()
            if not text_content:
                logger.warning(f"No text extracted from {pdf_link.title}")
                return None
            
            processed_doc = ProcessedDocument(
                title=pdf_link.title,
                url=str(pdf_link.url),
                content=text_content,
                pages=num_pages,
                processedAt=datetime.now().isoformat(),
                success=True
            )
            
            logger.info(f"Successfully processed {pdf_link.title}: {num_pages} pages, {len(text_content)} characters")
            return processed_doc
            
        finally:
            # Clean up temporary file
            os.unlink(temp_file_path)
            
    except Exception as e:
        logger.error(f"Error processing PDF {pdf_link.title}: {str(e)}")
        return ProcessedDocument(
            title=pdf_link.title,
            url=str(pdf_link.url),
            content="",
            pages=0,
            processedAt=datetime.now().isoformat(),
            success=False
        )

async def create_embedding(text: str) -> List[float]:
    """Create embedding using AWS Bedrock Titan"""
    try:
        # Truncate text if too long (Titan has limits)
        max_length = 8000
        if len(text) > max_length:
            text = text[:max_length]
        
        body = json.dumps({
            "inputText": text
        })
        
        response = bedrock_runtime.invoke_model(
            modelId="amazon.titan-embed-text-v2:0",
            body=body
        )
        
        response_body = json.loads(response['body'].read())
        return response_body['embedding']
        
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

def find_relevant_documents(question: str, top_k: int = 3) -> List[Dict[str, Any]]:
    if not embeddings_store:
        return []
    
    try:
        # Create embedding for the question
        question_embedding = asyncio.run(create_embedding(question))
        
        # Calculate similarities
        similarities = []
        for item in embeddings_store:
            similarity = cosine_similarity(
                [question_embedding], 
                [item['embedding']]
            )[0][0]
            similarities.append({
                'document': item['document'],
                'similarity': similarity,
                'chunk_index': item.get('chunk_index', 0)
            })
        
        # Sort by similarity and return top_k
        similarities.sort(key=lambda x: x['similarity'], reverse=True)
        return similarities[:top_k]
        
    except Exception as e:
        logger.error(f"Error finding relevant documents: {str(e)}")
        return []

# API Endpoints
@app.get("/")
async def root():
    return {
        "message": "NC DHHS PDF Q&A API",
        "version": "1.0.0",
        "documents_processed": len(document_store)
    }

@app.post("/extract-pdf-links")
async def extract_pdf_links(request: ExtractLinksRequest):
    """Extract PDF links from a website"""
    try:
        pdf_links = await extract_pdf_links_from_website(str(request.url))
        return {
            "pdf_links": [link.dict() for link in pdf_links],
            "count": len(pdf_links)
        }
    except Exception as e:
        logger.error(f"Error in extract_pdf_links: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/process-pdf-batch")
async def process_pdf_batch(request: ProcessPDFBatchRequest):
    """Process a batch of PDFs"""
    try:
        results = []
        
        # Process PDFs concurrently (but limit concurrency)
        semaphore = asyncio.Semaphore(3)  # Limit to 3 concurrent downloads
        
        async def process_with_semaphore(pdf_link):
            async with semaphore:
                return await download_and_process_pdf(pdf_link)
        
        tasks = [process_with_semaphore(pdf_link) for pdf_link in request.pdf_links]
        processed_docs = await asyncio.gather(*tasks, return_exceptions=True)
        
        for doc in processed_docs:
            if isinstance(doc, Exception):
                logger.error(f"Error processing PDF: {str(doc)}")
                continue
            if doc and doc.success:
                results.append(doc.dict())
                # Add to global store
                document_store.append(doc.dict())
        
        return {
            "results": results,
            "processed_count": len(results),
            "total_requested": len(request.pdf_links)
        }
        
    except Exception as e:
        logger.error(f"Error in process_pdf_batch: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/create-knowledge-base")
async def create_knowledge_base(request: CreateKnowledgeBaseRequest):
    """Create knowledge base with embeddings"""
    try:
        global embeddings_store
        embeddings_store = []
        
        for doc in request.documents:
            if not doc.get('content'):
                continue
                
            # Split document into chunks for better retrieval
            content = doc['content']
            chunk_size = 1000
            overlap = 200
            
            chunks = []
            for i in range(0, len(content), chunk_size - overlap):
                chunk = content[i:i + chunk_size]
                if chunk.strip():
                    chunks.append(chunk)
            
            # Create embeddings for each chunk
            for chunk_index, chunk in enumerate(chunks):
                try:
                    embedding = await create_embedding(chunk)
                    embeddings_store.append({
                        'document': {
                            'title': doc['title'],
                            'url': doc.get('url', ''),
                            'content': chunk,
                            'full_content': content,
                            'pages': doc.get('pages', 0)
                        },
                        'embedding': embedding,
                        'chunk_index': chunk_index
                    })
                except Exception as e:
                    logger.error(f"Error creating embedding for chunk {chunk_index} of {doc['title']}: {str(e)}")
                    continue
        
        return {
            "message": "Knowledge base created successfully",
            "documents_processed": len(request.documents),
            "embeddings_created": len(embeddings_store)
        }
        
    except Exception as e:
        logger.error(f"Error creating knowledge base: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ask-question")
async def ask_question(request: AskQuestionRequest):
    """Answer a question based on processed documents"""
    try:
        if not embeddings_store:
            raise HTTPException(
                status_code=400, 
                detail="No knowledge base available. Please process documents first."
            )
        
        # Find relevant documents
        relevant_docs = find_relevant_documents(request.question, top_k=5)
        
        if not relevant_docs:
            return {
                "answer": "I don't have enough information to answer that question based on the processed documents.",
                "sources": []
            }
        
        # Prepare context from relevant documents
        context_parts = []
        sources = []
        
        for item in relevant_docs:
            doc = item['document']
            context_parts.append(f"From '{doc['title']}':\n{doc['content']}\n")
            sources.append({
                'title': doc['title'],
                'url': doc.get('url', ''),
                'similarity': round(item['similarity'], 3)
            })
        
        context = "\n".join(context_parts)
        
        # Get answer from Bedrock
        answer = await query_bedrock(request.question, context)
        
        return {
            "answer": answer,
            "sources": sources,
            "context_length": len(context)
        }
        
    except Exception as e:
        logger.error(f"Error answering question: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/documents")
async def get_documents():
    """Get list of processed documents"""
    return {
        "documents": document_store,
        "count": len(document_store)
    }

@app.delete("/documents")
async def clear_documents():
    """Clear all processed documents"""
    global document_store, embeddings_store
    document_store = []
    embeddings_store = []
    return {"message": "All documents cleared"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "documents_count": len(document_store),
        "embeddings_count": len(embeddings_store)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
