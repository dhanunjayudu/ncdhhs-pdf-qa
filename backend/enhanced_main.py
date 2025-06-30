import os
import json
import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import tempfile
import aiofiles
import uuid
from concurrent.futures import ThreadPoolExecutor

import boto3
from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
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
    title="NCDHHS PDF Q&A API - Enhanced",
    description="Enhanced PDF processing and Q&A system with async processing",
    version="2.0.0"
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
AWS_PROFILE = os.getenv('AWS_PROFILE')

# Initialize AWS session
if AWS_PROFILE:
    session = boto3.Session(profile_name=AWS_PROFILE)
else:
    session = boto3.Session()

s3_client = session.client('s3', region_name=AWS_REGION)
bedrock_client = session.client('bedrock-runtime', region_name=AWS_REGION)
bedrock_agent_client = session.client('bedrock-agent', region_name=AWS_REGION)

# Job tracking
class ProcessingJob:
    def __init__(self, job_id: str, total_pdfs: int, job_type: str = "pdf_processing"):
        self.job_id = job_id
        self.total_pdfs = total_pdfs
        self.processed = 0
        self.failed = 0
        self.status = "queued"  # queued, processing, completed, failed
        self.results = []
        self.error_messages = []
        self.created_at = datetime.utcnow()
        self.job_type = job_type
        self.websocket_connections = []

# In-memory job storage (use Redis in production)
active_jobs: Dict[str, ProcessingJob] = {}

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket, job_id: str):
        await websocket.accept()
        self.active_connections.append(websocket)
        if job_id in active_jobs:
            active_jobs[job_id].websocket_connections.append(websocket)

    def disconnect(self, websocket: WebSocket, job_id: str):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if job_id in active_jobs and websocket in active_jobs[job_id].websocket_connections:
            active_jobs[job_id].websocket_connections.remove(websocket)

    async def send_progress_update(self, job_id: str, message: dict):
        if job_id in active_jobs:
            job = active_jobs[job_id]
            disconnected = []
            for connection in job.websocket_connections:
                try:
                    await connection.send_json(message)
                except:
                    disconnected.append(connection)
            
            # Remove disconnected connections
            for conn in disconnected:
                job.websocket_connections.remove(conn)

manager = ConnectionManager()

# Pydantic models
class URLRequest(BaseModel):
    url: HttpUrl
    max_pdfs: Optional[int] = 50
    processing_mode: Optional[str] = "async"  # "sync" or "async"

class QuestionRequest(BaseModel):
    question: str
    max_results: Optional[int] = 5

class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    progress: Dict[str, Any]
    results: List[Dict[str, Any]]
    error_messages: List[str]
    created_at: datetime

# Enhanced PDF Processing Functions
async def extract_pdf_links_enhanced(url: str) -> List[str]:
    """Enhanced PDF link extraction with better error handling"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        pdf_links = []
        
        # Find all links that might be PDFs
        for link in soup.find_all('a', href=True):
            href = link['href']
            if href.lower().endswith('.pdf'):
                full_url = urljoin(url, href)
                pdf_links.append(full_url)
        
        # Also check for embedded PDFs and object tags
        for obj in soup.find_all(['object', 'embed'], type='application/pdf'):
            if obj.get('data'):
                full_url = urljoin(url, obj['data'])
                pdf_links.append(full_url)
        
        logger.info(f"Found {len(pdf_links)} PDF links on {url}")
        return list(set(pdf_links))  # Remove duplicates
        
    except Exception as e:
        logger.error(f"Error extracting PDF links from {url}: {str(e)}")
        raise HTTPException(status_code=400, f"Failed to extract PDF links: {str(e)}")

async def process_single_pdf_optimized(pdf_url: str, job_id: str) -> Dict[str, Any]:
    """Process a single PDF with optimized storage (OpenSearch only)"""
    try:
        # Download PDF
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(pdf_url, headers=headers, timeout=60)
        response.raise_for_status()
        
        # Extract text
        pdf_reader = pypdf.PdfReader(io.BytesIO(response.content))
        text_content = ""
        
        for page in pdf_reader.pages:
            text_content += page.extract_text() + "\n"
        
        if not text_content.strip():
            return {"url": pdf_url, "status": "failed", "error": "No text content found"}
        
        # Create document chunks for better search
        chunks = create_text_chunks(text_content, chunk_size=1000)
        
        # Generate document ID
        doc_id = str(uuid.uuid4())
        
        # Store in OpenSearch only (no S3 redundancy)
        document = {
            "doc_id": doc_id,
            "source_url": pdf_url,
            "title": extract_title_from_url(pdf_url),
            "content": text_content,
            "content_length": len(text_content),
            "chunks": chunks,
            "chunk_count": len(chunks),
            "processed_at": datetime.utcnow().isoformat(),
            "job_id": job_id,
            "file_size": len(response.content)
        }
        
        # Index in OpenSearch
        await index_document_in_opensearch(document)
        
        return {
            "url": pdf_url,
            "doc_id": doc_id,
            "status": "success",
            "chunks": len(chunks),
            "content_length": len(text_content)
        }
        
    except Exception as e:
        logger.error(f"Error processing PDF {pdf_url}: {str(e)}")
        return {"url": pdf_url, "status": "failed", "error": str(e)}

def create_text_chunks(text: str, chunk_size: int = 1000, overlap: int = 100) -> List[str]:
    """Create overlapping text chunks for better search"""
    words = text.split()
    chunks = []
    
    for i in range(0, len(words), chunk_size - overlap):
        chunk = ' '.join(words[i:i + chunk_size])
        if chunk.strip():
            chunks.append(chunk)
    
    return chunks

def extract_title_from_url(url: str) -> str:
    """Extract a meaningful title from PDF URL"""
    parsed = urlparse(url)
    filename = os.path.basename(parsed.path)
    if filename.endswith('.pdf'):
        return filename[:-4].replace('_', ' ').replace('-', ' ').title()
    return filename or "Untitled Document"

async def index_document_in_opensearch(document: Dict[str, Any]):
    """Index document in OpenSearch with proper error handling"""
    try:
        # This would be implemented with your OpenSearch client
        # For now, we'll simulate the indexing
        logger.info(f"Indexing document {document['doc_id']} in OpenSearch")
        # opensearch_client.index(index="ncdhhs-documents", id=document['doc_id'], body=document)
        
    except Exception as e:
        logger.error(f"Error indexing document in OpenSearch: {str(e)}")
        raise

async def process_pdfs_background(job_id: str, pdf_urls: List[str]):
    """Background processing with progress tracking and WebSocket updates"""
    job = active_jobs[job_id]
    job.status = "processing"
    
    # Send initial progress update
    await manager.send_progress_update(job_id, {
        "type": "started",
        "job_id": job_id,
        "total": len(pdf_urls),
        "message": f"Starting to process {len(pdf_urls)} PDFs..."
    })
    
    # Process PDFs with controlled concurrency
    semaphore = asyncio.Semaphore(5)  # Max 5 concurrent downloads
    
    async def process_with_semaphore(url: str, index: int):
        async with semaphore:
            result = await process_single_pdf_optimized(url, job_id)
            
            if result["status"] == "success":
                job.processed += 1
            else:
                job.failed += 1
                job.error_messages.append(f"Failed to process {url}: {result.get('error', 'Unknown error')}")
            
            job.results.append(result)
            
            # Send progress update
            await manager.send_progress_update(job_id, {
                "type": "progress",
                "job_id": job_id,
                "current": index + 1,
                "total": len(pdf_urls),
                "processed": job.processed,
                "failed": job.failed,
                "percentage": ((index + 1) / len(pdf_urls)) * 100,
                "message": f"Processed {index + 1}/{len(pdf_urls)} PDFs",
                "latest_result": result
            })
            
            return result
    
    # Process all PDFs
    tasks = [process_with_semaphore(url, i) for i, url in enumerate(pdf_urls)]
    await asyncio.gather(*tasks, return_exceptions=True)
    
    # Mark job as completed
    job.status = "completed" if job.failed == 0 else "completed_with_errors"
    
    # Send completion update
    await manager.send_progress_update(job_id, {
        "type": "completed",
        "job_id": job_id,
        "processed": job.processed,
        "failed": job.failed,
        "total": len(pdf_urls),
        "message": f"Processing completed: {job.processed} successful, {job.failed} failed"
    })

# API Endpoints
@app.post("/extract-pdf-links")
async def extract_pdf_links_endpoint(request: URLRequest):
    """Extract PDF links from a website"""
    try:
        pdf_links = await extract_pdf_links_enhanced(str(request.url))
        return {
            "url": str(request.url),
            "pdf_links": pdf_links,
            "count": len(pdf_links),
            "message": f"Found {len(pdf_links)} PDF links"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/process-website-async")
async def process_website_async(request: URLRequest, background_tasks: BackgroundTasks):
    """Process website PDFs asynchronously with job tracking"""
    try:
        # Extract PDF links first
        pdf_links = await extract_pdf_links_enhanced(str(request.url))
        
        if not pdf_links:
            raise HTTPException(status_code=404, detail="No PDF links found on the website")
        
        # Limit PDFs if requested
        if request.max_pdfs and len(pdf_links) > request.max_pdfs:
            pdf_links = pdf_links[:request.max_pdfs]
        
        # Create processing job
        job_id = str(uuid.uuid4())
        job = ProcessingJob(job_id, len(pdf_links))
        active_jobs[job_id] = job
        
        if request.processing_mode == "sync" and len(pdf_links) <= 5:
            # Process small batches synchronously
            job.status = "processing"
            results = []
            for i, url in enumerate(pdf_links):
                result = await process_single_pdf_optimized(url, job_id)
                results.append(result)
                if result["status"] == "success":
                    job.processed += 1
                else:
                    job.failed += 1
            
            job.status = "completed"
            job.results = results
            
            return {
                "job_id": job_id,
                "status": "completed",
                "processing_mode": "sync",
                "results": results,
                "processed": job.processed,
                "failed": job.failed
            }
        else:
            # Use background processing for larger batches
            background_tasks.add_task(process_pdfs_background, job_id, pdf_links)
            
            return {
                "job_id": job_id,
                "status": "queued",
                "processing_mode": "async",
                "total_pdfs": len(pdf_links),
                "estimated_time_minutes": len(pdf_links) * 1.5,
                "progress_endpoint": f"/job-status/{job_id}",
                "websocket_endpoint": f"/ws/progress/{job_id}"
            }
            
    except Exception as e:
        logger.error(f"Error in process_website_async: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/job-status/{job_id}")
async def get_job_status(job_id: str) -> JobStatusResponse:
    """Get processing job status"""
    if job_id not in active_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = active_jobs[job_id]
    return JobStatusResponse(
        job_id=job_id,
        status=job.status,
        progress={
            "processed": job.processed,
            "failed": job.failed,
            "total": job.total_pdfs,
            "percentage": (job.processed + job.failed) / job.total_pdfs * 100 if job.total_pdfs > 0 else 0
        },
        results=job.results,
        error_messages=job.error_messages,
        created_at=job.created_at
    )

@app.websocket("/ws/progress/{job_id}")
async def websocket_progress(websocket: WebSocket, job_id: str):
    """Real-time progress updates via WebSocket"""
    await manager.connect(websocket, job_id)
    try:
        while True:
            # Keep connection alive and send periodic updates
            if job_id in active_jobs:
                job = active_jobs[job_id]
                await websocket.send_json({
                    "job_id": job_id,
                    "status": job.status,
                    "processed": job.processed,
                    "failed": job.failed,
                    "total": job.total_pdfs,
                    "percentage": (job.processed + job.failed) / job.total_pdfs * 100 if job.total_pdfs > 0 else 0,
                    "timestamp": datetime.utcnow().isoformat()
                })
                
                if job.status in ["completed", "completed_with_errors", "failed"]:
                    break
            
            await asyncio.sleep(2)  # Update every 2 seconds
            
    except WebSocketDisconnect:
        manager.disconnect(websocket, job_id)

@app.delete("/job/{job_id}")
async def cancel_job(job_id: str):
    """Cancel a processing job"""
    if job_id not in active_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = active_jobs[job_id]
    if job.status in ["completed", "failed"]:
        raise HTTPException(status_code=400, detail="Cannot cancel completed job")
    
    job.status = "cancelled"
    return {"message": f"Job {job_id} cancelled successfully"}

@app.get("/jobs")
async def list_jobs():
    """List all processing jobs"""
    jobs = []
    for job_id, job in active_jobs.items():
        jobs.append({
            "job_id": job_id,
            "status": job.status,
            "total_pdfs": job.total_pdfs,
            "processed": job.processed,
            "failed": job.failed,
            "created_at": job.created_at
        })
    
    return {"jobs": jobs, "total": len(jobs)}

# Health check
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "active_jobs": len(active_jobs),
        "version": "2.0.0"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
