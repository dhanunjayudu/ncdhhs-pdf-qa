import os
import json
import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import tempfile
import aiofiles
import uuid
import boto3
import requests
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from bs4 import BeautifulSoup
import pypdf
from urllib.parse import urljoin, urlparse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="NCDHHS PDF Q&A API - Bedrock Knowledge Base",
    description="PDF processing with Bedrock Knowledge Base integration",
    version="4.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# AWS Configuration
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')

# Bedrock Knowledge Base Configuration
S3_KNOWLEDGE_BASE_BUCKET = os.getenv('S3_KNOWLEDGE_BASE_BUCKET', 'ncdhhs-pdf-qa-dev-bedrock-kb-f04187f9')
BEDROCK_KNOWLEDGE_BASE_ID = os.getenv('BEDROCK_KNOWLEDGE_BASE_ID', 'EJRS8I2F6J')
BEDROCK_DATA_SOURCE_ID = os.getenv('BEDROCK_DATA_SOURCE_ID', 'PGYK8O2WDY')
BEDROCK_PRIMARY_MODEL = os.getenv('BEDROCK_PRIMARY_MODEL', 'amazon.nova-pro-v1:0')
BEDROCK_GUARDRAIL_ID = os.getenv('BEDROCK_GUARDRAIL_ID', 'd6wcptfamw16')
BEDROCK_GUARDRAIL_VERSION = os.getenv('BEDROCK_GUARDRAIL_VERSION', 'DRAFT')
OPENSEARCH_COLLECTION_ARN = os.getenv('OPENSEARCH_COLLECTION_ARN', 'arn:aws:aoss:us-east-1:942713336312:collection/14dzr3m6d071boqiytt6')

# Initialize AWS session - Use default credentials (ECS task role)
# Explicitly avoid using any profile by clearing profile environment variables
if 'AWS_PROFILE' in os.environ:
    del os.environ['AWS_PROFILE']
if 'AWS_DEFAULT_PROFILE' in os.environ:
    del os.environ['AWS_DEFAULT_PROFILE']

# Initialize boto3 session without any profile
session = boto3.Session(profile_name=None)

# Initialize AWS clients
s3_client = session.client('s3', region_name=AWS_REGION)
bedrock_runtime = session.client('bedrock-runtime', region_name=AWS_REGION)
bedrock_agent = session.client('bedrock-agent', region_name=AWS_REGION)
bedrock_agent_runtime = session.client('bedrock-agent-runtime', region_name=AWS_REGION)

# Global variables for processing status
processing_status = {
    "status": "idle",
    "progress": 0,
    "message": "Ready to process documents",
    "processed_count": 0,
    "total_count": 0,
    "current_url": "",
    "errors": []
}

# Pydantic models
class URLRequest(BaseModel):
    url: HttpUrl
    max_depth: int = 2

class QuestionRequest(BaseModel):
    question: str
    max_results: int = 5

class ProcessingStatus(BaseModel):
    status: str
    progress: int
    message: str
    processed_count: int
    total_count: int
    current_url: str
    errors: List[str]

class AnswerResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]
    confidence: float
    processing_time: float

# Utility functions
def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """Extract text from PDF bytes"""
    try:
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            temp_file.write(pdf_bytes)
            temp_file.flush()
            
            with open(temp_file.name, 'rb') as file:
                pdf_reader = pypdf.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
            
            os.unlink(temp_file.name)
            return text.strip()
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {e}")
        return ""

def generate_s3_key(url: str) -> str:
    """Generate S3 key with timestamp for uploaded PDF"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.basename(urlparse(url).path)
    if not filename.endswith('.pdf'):
        filename += '.pdf'
    return f"documents/{timestamp}_{filename}"

async def upload_pdf_to_s3(pdf_bytes: bytes, s3_key: str, source_url: str) -> bool:
    """Upload PDF to S3 Knowledge Base bucket"""
    try:
        # Add metadata
        metadata = {
            'source-url': source_url,
            'upload-timestamp': datetime.now().isoformat(),
            'content-type': 'application/pdf'
        }
        
        s3_client.put_object(
            Bucket=S3_KNOWLEDGE_BASE_BUCKET,
            Key=s3_key,
            Body=pdf_bytes,
            ContentType='application/pdf',
            Metadata=metadata
        )
        
        logger.info(f"Successfully uploaded {s3_key} to S3")
        return True
    except Exception as e:
        logger.error(f"Error uploading to S3: {e}")
        return False

def start_knowledge_base_sync():
    """Start Knowledge Base ingestion job"""
    try:
        response = bedrock_agent.start_ingestion_job(
            knowledgeBaseId=BEDROCK_KNOWLEDGE_BASE_ID,
            dataSourceId=BEDROCK_DATA_SOURCE_ID
        )
        
        job_id = response['ingestionJob']['ingestionJobId']
        logger.info(f"Started ingestion job: {job_id}")
        return job_id
    except Exception as e:
        logger.error(f"Error starting ingestion job: {e}")
        return None

def get_ingestion_job_status(job_id: str) -> Dict[str, Any]:
    """Get status of ingestion job"""
    try:
        response = bedrock_agent.get_ingestion_job(
            knowledgeBaseId=BEDROCK_KNOWLEDGE_BASE_ID,
            dataSourceId=BEDROCK_DATA_SOURCE_ID,
            ingestionJobId=job_id
        )
        return response['ingestionJob']
    except Exception as e:
        logger.error(f"Error getting ingestion job status: {e}")
        return {}

async def find_pdf_links(url: str, max_depth: int = 2, visited: set = None) -> List[str]:
    """Find PDF links on a webpage"""
    if visited is None:
        visited = set()
    
    if url in visited or max_depth <= 0:
        return []
    
    visited.add(url)
    pdf_links = []
    
    try:
        response = requests.get(url, timeout=30, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find all links
        for link in soup.find_all('a', href=True):
            href = link['href']
            full_url = urljoin(url, href)
            
            if full_url.lower().endswith('.pdf'):
                pdf_links.append(full_url)
            elif max_depth > 1 and full_url not in visited:
                # Recursively search linked pages
                sub_links = await find_pdf_links(full_url, max_depth - 1, visited)
                pdf_links.extend(sub_links)
        
        return list(set(pdf_links))  # Remove duplicates
        
    except Exception as e:
        logger.error(f"Error finding PDF links on {url}: {e}")
        return []

async def process_pdfs_background(url: str, max_depth: int):
    """Background task to process PDFs"""
    global processing_status
    
    try:
        processing_status.update({
            "status": "finding_pdfs",
            "progress": 10,
            "message": "Searching for PDF documents...",
            "current_url": str(url),
            "errors": []
        })
        
        # Find PDF links
        pdf_links = await find_pdf_links(str(url), max_depth)
        
        if not pdf_links:
            processing_status.update({
                "status": "completed",
                "progress": 100,
                "message": "No PDF documents found",
                "total_count": 0
            })
            return
        
        processing_status.update({
            "status": "processing",
            "progress": 20,
            "message": f"Found {len(pdf_links)} PDF documents. Processing...",
            "total_count": len(pdf_links)
        })
        
        uploaded_count = 0
        
        for i, pdf_url in enumerate(pdf_links):
            try:
                processing_status.update({
                    "current_url": pdf_url,
                    "message": f"Processing PDF {i+1} of {len(pdf_links)}"
                })
                
                # Download PDF
                response = requests.get(pdf_url, timeout=60)
                response.raise_for_status()
                
                # Generate S3 key
                s3_key = generate_s3_key(pdf_url)
                
                # Upload to S3
                if await upload_pdf_to_s3(response.content, s3_key, pdf_url):
                    uploaded_count += 1
                    processing_status["processed_count"] = uploaded_count
                
                # Update progress
                progress = 20 + (70 * (i + 1) // len(pdf_links))
                processing_status["progress"] = progress
                
            except Exception as e:
                error_msg = f"Error processing {pdf_url}: {str(e)}"
                logger.error(error_msg)
                processing_status["errors"].append(error_msg)
        
        # Start Knowledge Base sync
        processing_status.update({
            "status": "syncing",
            "progress": 90,
            "message": "Syncing with Knowledge Base..."
        })
        
        job_id = start_knowledge_base_sync()
        
        if job_id:
            processing_status.update({
                "status": "completed",
                "progress": 100,
                "message": f"Successfully processed {uploaded_count} PDFs and started Knowledge Base sync",
                "processed_count": uploaded_count
            })
        else:
            processing_status.update({
                "status": "completed_with_warnings",
                "progress": 100,
                "message": f"Uploaded {uploaded_count} PDFs but failed to start Knowledge Base sync",
                "processed_count": uploaded_count
            })
            
    except Exception as e:
        error_msg = f"Processing failed: {str(e)}"
        logger.error(error_msg)
        processing_status.update({
            "status": "failed",
            "progress": 0,
            "message": error_msg,
            "errors": [error_msg]
        })

def query_knowledge_base(question: str, max_results: int = 5) -> Dict[str, Any]:
    """Query the Bedrock Knowledge Base"""
    try:
        start_time = datetime.now()
        
        # Retrieve relevant documents
        retrieve_response = bedrock_agent_runtime.retrieve(
            knowledgeBaseId=BEDROCK_KNOWLEDGE_BASE_ID,
            retrievalQuery={'text': question},
            retrievalConfiguration={
                'vectorSearchConfiguration': {
                    'numberOfResults': max_results
                }
            }
        )
        
        retrieval_results = retrieve_response.get('retrievalResults', [])
        
        if not retrieval_results:
            return {
                "answer": "I couldn't find any relevant information in the NCDHHS documents to answer your question.",
                "sources": [],
                "confidence": 0.0,
                "processing_time": (datetime.now() - start_time).total_seconds()
            }
        
        # Check if the top result has a reasonable confidence score
        top_score = retrieval_results[0].get('score', 0.0) if retrieval_results else 0.0
        
        # If the confidence is too low, the question is likely irrelevant
        if top_score < 0.5:  # Increased threshold for relevance
            return {
                "answer": f"I couldn't find relevant information in the NCDHHS documents to answer your question about '{question}'. The available documents appear to contain information about software licensing and legal agreements, which may not be related to your query.",
                "sources": [],
                "confidence": 0.0,
                "processing_time": (datetime.now() - start_time).total_seconds()
            }
        
        # Prepare context for generation
        context = "\n\n".join([
            f"Source: {result.get('location', {}).get('s3Location', {}).get('uri', 'Unknown')}\n"
            f"Content: {result.get('content', {}).get('text', '')}"
            for result in retrieval_results
        ])
        
        # Generate answer using Bedrock with improved prompt
        prompt = f"""You are an AI assistant that answers questions based on NCDHHS (North Carolina Department of Health and Human Services) documents. 

Based on the following context from NCDHHS documents, please provide a comprehensive answer to the question. 

IMPORTANT INSTRUCTIONS:
1. If the question is not related to health, human services, or government services, politely explain that you can only answer questions about NCDHHS topics.
2. If the context doesn't contain relevant information to answer the question, clearly state that the information is not available in the provided documents.
3. Only use information from the provided context - do not add external knowledge.
4. If the context seems to be about unrelated topics (like software licensing), mention this discrepancy.

Context from NCDHHS documents:
{context}

Question: {question}

Answer:"""
        
        generate_response = bedrock_runtime.invoke_model(
            modelId=BEDROCK_PRIMARY_MODEL,
            body=json.dumps({
                "schemaVersion": "messages-v1",
                "messages": [
                    {
                        "role": "user",
                        "content": [{"text": prompt}]
                    }
                ],
                "inferenceConfig": {
                    "maxTokens": 1000,
                    "temperature": 0.1
                }
            }),
            contentType='application/json'
        )
        
        response_body = json.loads(generate_response['body'].read())
        answer = response_body['output']['message']['content'][0]['text']
        
        # Prepare sources only if they're relevant (score > threshold)
        sources = []
        for result in retrieval_results:
            score = result.get('score', 0.0)
            if score >= 0.5:  # Only include sources with reasonable confidence
                source_info = {
                    "uri": result.get('location', {}).get('s3Location', {}).get('uri', 'Unknown'),
                    "score": score,
                    "excerpt": result.get('content', {}).get('text', '')[:300] + "..." if len(result.get('content', {}).get('text', '')) > 300 else result.get('content', {}).get('text', '')
                }
                sources.append(source_info)
        
        # Calculate confidence based on top result score
        confidence = top_score
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return {
            "answer": answer,
            "sources": sources,
            "confidence": confidence,
            "processing_time": processing_time
        }
        
    except Exception as e:
        logger.error(f"Error querying knowledge base: {e}")
        return {
            "answer": f"I encountered an error while processing your question: {str(e)}",
            "sources": [],
            "confidence": 0.0,
            "processing_time": 0.0
        }

# API Endpoints
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "NCDHHS PDF Q&A API - Bedrock Knowledge Base",
        "version": "4.0.0",
        "architecture": "S3 + Bedrock Knowledge Base + OpenSearch Serverless",
        "knowledge_base_id": BEDROCK_KNOWLEDGE_BASE_ID,
        "status": "active"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test AWS connectivity
        s3_client.head_bucket(Bucket=S3_KNOWLEDGE_BASE_BUCKET)
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "services": {
                "s3": "connected",
                "bedrock": "connected",
                "knowledge_base": BEDROCK_KNOWLEDGE_BASE_ID
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.post("/process-and-upload-pdfs")
async def process_and_upload_pdfs(request: URLRequest, background_tasks: BackgroundTasks):
    """Process PDFs from a website and upload to Knowledge Base"""
    global processing_status
    
    if processing_status["status"] == "processing":
        raise HTTPException(status_code=409, detail="Processing already in progress")
    
    # Reset processing status
    processing_status = {
        "status": "starting",
        "progress": 0,
        "message": "Starting PDF processing...",
        "processed_count": 0,
        "total_count": 0,
        "current_url": str(request.url),
        "errors": []
    }
    
    # Start background processing
    background_tasks.add_task(process_pdfs_background, request.url, request.max_depth)
    
    return {
        "message": "PDF processing started",
        "status": "processing",
        "url": str(request.url),
        "max_depth": request.max_depth
    }

@app.get("/processing-status", response_model=ProcessingStatus)
async def get_processing_status():
    """Get current processing status"""
    return ProcessingStatus(**processing_status)

@app.post("/ask-question", response_model=AnswerResponse)
async def ask_question(request: QuestionRequest):
    """Ask a question using the Knowledge Base"""
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    
    result = query_knowledge_base(request.question, request.max_results)
    
    return AnswerResponse(
        answer=result["answer"],
        sources=result["sources"],
        confidence=result["confidence"],
        processing_time=result["processing_time"]
    )

@app.post("/clear-processing-status")
async def clear_processing_status():
    """Clear stale processing status"""
    global processing_status
    processing_status = {
        "status": "idle",
        "progress": 0,
        "message": "Ready to process documents",
        "processed_count": 0,
        "total_count": 0,
        "current_url": "",
        "errors": []
    }
    return {
        "message": "Processing status cleared successfully",
        "status": processing_status
    }

@app.get("/detailed-status")
async def get_detailed_status():
    """Get detailed status including S3 documents, ingestion jobs, and sync status"""
    try:
        # Get S3 document count
        s3_response = s3_client.list_objects_v2(
            Bucket=S3_KNOWLEDGE_BASE_BUCKET,
            Prefix="documents/"
        )
        s3_document_count = s3_response.get('KeyCount', 0)
        s3_documents = []
        
        if 'Contents' in s3_response:
            for obj in s3_response['Contents']:
                s3_documents.append({
                    "key": obj['Key'],
                    "size": obj['Size'],
                    "last_modified": obj['LastModified'].isoformat(),
                    "filename": obj['Key'].split('/')[-1] if '/' in obj['Key'] else obj['Key']
                })
        
        # Get Knowledge Base info
        kb_response = bedrock_agent.get_knowledge_base(
            knowledgeBaseId=BEDROCK_KNOWLEDGE_BASE_ID
        )
        
        # Get Data Source info
        ds_response = bedrock_agent.get_data_source(
            knowledgeBaseId=BEDROCK_KNOWLEDGE_BASE_ID,
            dataSourceId=BEDROCK_DATA_SOURCE_ID
        )
        
        # List recent ingestion jobs with more details
        jobs_response = bedrock_agent.list_ingestion_jobs(
            knowledgeBaseId=BEDROCK_KNOWLEDGE_BASE_ID,
            dataSourceId=BEDROCK_DATA_SOURCE_ID,
            maxResults=10
        )
        
        # Get the most recent ingestion job details
        latest_job = None
        if jobs_response.get('ingestionJobSummaries'):
            latest_job_summary = jobs_response['ingestionJobSummaries'][0]
            try:
                latest_job_detail = bedrock_agent.get_ingestion_job(
                    knowledgeBaseId=BEDROCK_KNOWLEDGE_BASE_ID,
                    dataSourceId=BEDROCK_DATA_SOURCE_ID,
                    ingestionJobId=latest_job_summary['ingestionJobId']
                )
                latest_job = latest_job_detail['ingestionJob']
            except Exception as e:
                logger.warning(f"Could not get latest job details: {e}")
                latest_job = latest_job_summary
        
        # Determine sync status
        sync_status = "unknown"
        sync_message = "Unable to determine sync status"
        
        if latest_job:
            job_status = latest_job.get('status', 'UNKNOWN')
            if job_status == 'COMPLETE':
                sync_status = "synced"
                sync_message = "Knowledge Base is up to date with S3"
            elif job_status == 'IN_PROGRESS':
                sync_status = "syncing"
                sync_message = "Knowledge Base sync in progress"
            elif job_status == 'FAILED':
                sync_status = "failed"
                sync_message = "Last sync failed"
            else:
                sync_status = "pending"
                sync_message = f"Sync status: {job_status}"
        elif s3_document_count > 0:
            sync_status = "out_of_sync"
            sync_message = "Documents in S3 but no recent ingestion jobs"
        else:
            sync_status = "empty"
            sync_message = "No documents in S3"
        
        return {
            "timestamp": datetime.now().isoformat(),
            "s3_status": {
                "bucket": S3_KNOWLEDGE_BASE_BUCKET,
                "document_count": s3_document_count,
                "documents": s3_documents[:10],  # Limit to first 10 for UI
                "total_size_bytes": sum(doc['size'] for doc in s3_documents)
            },
            "knowledge_base": {
                "id": BEDROCK_KNOWLEDGE_BASE_ID,
                "name": kb_response['knowledgeBase']['name'],
                "status": kb_response['knowledgeBase']['status'],
                "description": kb_response['knowledgeBase'].get('description', '')
            },
            "data_source": {
                "id": BEDROCK_DATA_SOURCE_ID,
                "name": ds_response['dataSource']['name'],
                "status": ds_response['dataSource']['status'],
                "description": ds_response['dataSource'].get('description', '')
            },
            "sync_status": {
                "status": sync_status,
                "message": sync_message,
                "last_sync_time": latest_job.get('updatedAt') if latest_job else None
            },
            "latest_ingestion_job": latest_job,
            "recent_ingestion_jobs": jobs_response.get('ingestionJobSummaries', []),
            "processing_status": processing_status
        }
        
    except Exception as e:
        logger.error(f"Error getting detailed status: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting detailed status: {str(e)}")

@app.post("/trigger-sync")
async def trigger_knowledge_base_sync():
    """Manually trigger Knowledge Base sync"""
    try:
        job_id = start_knowledge_base_sync()
        if job_id:
            return {
                "message": "Knowledge Base sync started successfully",
                "job_id": job_id,
                "status": "started"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to start Knowledge Base sync")
    except Exception as e:
        logger.error(f"Error triggering sync: {e}")
        raise HTTPException(status_code=500, detail=f"Error triggering sync: {str(e)}")

@app.post("/clear-processing-status")
async def clear_processing_status():
    """Clear stale processing status"""
    global processing_status
    processing_status = {
        "status": "idle",
        "progress": 0,
        "message": "Ready to process documents",
        "processed_count": 0,
        "total_count": 0,
        "current_url": "",
        "errors": []
    }
    return {
        "message": "Processing status cleared successfully",
        "status": processing_status
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
