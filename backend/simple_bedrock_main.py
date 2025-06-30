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
    title="NCDHHS PDF Q&A API - Simplified Bedrock",
    description="Simplified PDF processing with direct S3 + Bedrock Knowledge Base integration",
    version="3.0.0"
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

# Configuration from environment
S3_KNOWLEDGE_BASE_BUCKET = os.getenv('S3_KNOWLEDGE_BASE_BUCKET')
BEDROCK_KNOWLEDGE_BASE_ID = os.getenv('BEDROCK_KNOWLEDGE_BASE_ID')
BEDROCK_DATA_SOURCE_ID = os.getenv('BEDROCK_DATA_SOURCE_ID')
BEDROCK_GUARDRAIL_ID = os.getenv('BEDROCK_GUARDRAIL_ID')
BEDROCK_GUARDRAIL_VERSION = os.getenv('BEDROCK_GUARDRAIL_VERSION', '1')
BEDROCK_PRIMARY_MODEL = os.getenv('BEDROCK_PRIMARY_MODEL', 'amazon.nova-pro-v1:0')

# Pydantic models
class URLRequest(BaseModel):
    url: HttpUrl
    max_pdfs: Optional[int] = 50

class QuestionRequest(BaseModel):
    question: str
    use_guardrails: Optional[bool] = True
    max_results: Optional[int] = 5

class ProcessingStatus(BaseModel):
    status: str
    message: str
    processed: int
    failed: int
    total: int
    timestamp: datetime

# Global processing status
current_processing_status = None

async def extract_pdf_links_from_website(url: str) -> List[str]:
    """Extract PDF links from a website"""
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
        
        # Also check for embedded PDFs
        for obj in soup.find_all(['object', 'embed'], type='application/pdf'):
            if obj.get('data'):
                full_url = urljoin(url, obj['data'])
                pdf_links.append(full_url)
        
        logger.info(f"Found {len(pdf_links)} PDF links on {url}")
        return list(set(pdf_links))  # Remove duplicates
        
    except Exception as e:
        logger.error(f"Error extracting PDF links from {url}: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Failed to extract PDF links: {str(e)}")

async def download_and_upload_pdf_to_s3(pdf_url: str, s3_key: str) -> Dict[str, Any]:
    """Download PDF and upload directly to S3"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(pdf_url, headers=headers, timeout=60)
        response.raise_for_status()
        
        # Upload PDF to S3
        s3_client.put_object(
            Bucket=S3_KNOWLEDGE_BASE_BUCKET,
            Key=s3_key,
            Body=response.content,
            ContentType='application/pdf',
            Metadata={
                'source_url': pdf_url,
                'uploaded_at': datetime.utcnow().isoformat(),
                'content_length': str(len(response.content))
            }
        )
        
        logger.info(f"Uploaded PDF to S3: {s3_key}")
        
        return {
            'status': 'success',
            'url': pdf_url,
            's3_key': s3_key,
            'size': len(response.content)
        }
        
    except Exception as e:
        logger.error(f"Error processing PDF {pdf_url}: {str(e)}")
        return {
            'status': 'failed',
            'url': pdf_url,
            'error': str(e)
        }

async def sync_bedrock_knowledge_base():
    """Trigger Bedrock Knowledge Base synchronization"""
    try:
        if not BEDROCK_KNOWLEDGE_BASE_ID or not BEDROCK_DATA_SOURCE_ID:
            logger.warning("Bedrock Knowledge Base or Data Source ID not configured")
            return {"status": "skipped", "message": "Bedrock not configured"}
        
        # Start ingestion job
        response = bedrock_agent_client.start_ingestion_job(
            knowledgeBaseId=BEDROCK_KNOWLEDGE_BASE_ID,
            dataSourceId=BEDROCK_DATA_SOURCE_ID
        )
        
        job_id = response['ingestionJob']['ingestionJobId']
        logger.info(f"Started Bedrock ingestion job: {job_id}")
        
        return {
            "status": "started",
            "job_id": job_id,
            "message": "Knowledge base synchronization started"
        }
        
    except Exception as e:
        logger.error(f"Error syncing Bedrock Knowledge Base: {str(e)}")
        return {"status": "error", "message": str(e)}

# API Endpoints
@app.post("/extract-pdf-links")
async def extract_pdf_links_endpoint(request: URLRequest):
    """Extract PDF links from a website"""
    try:
        pdf_links = await extract_pdf_links_from_website(str(request.url))
        
        # Limit PDFs if requested
        if request.max_pdfs and len(pdf_links) > request.max_pdfs:
            pdf_links = pdf_links[:request.max_pdfs]
        
        return {
            "url": str(request.url),
            "pdf_links": pdf_links,
            "count": len(pdf_links),
            "message": f"Found {len(pdf_links)} PDF links"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/process-and-upload-pdfs")
async def process_and_upload_pdfs(request: URLRequest, background_tasks: BackgroundTasks):
    """Process PDFs and upload directly to S3 for Bedrock Knowledge Base"""
    global current_processing_status
    
    try:
        # Extract PDF links
        pdf_links = await extract_pdf_links_from_website(str(request.url))
        
        if not pdf_links:
            raise HTTPException(status_code=404, detail="No PDF links found on the website")
        
        # Limit PDFs if requested
        if request.max_pdfs and len(pdf_links) > request.max_pdfs:
            pdf_links = pdf_links[:request.max_pdfs]
        
        # Initialize processing status
        current_processing_status = ProcessingStatus(
            status="processing",
            message="Starting PDF processing...",
            processed=0,
            failed=0,
            total=len(pdf_links),
            timestamp=datetime.utcnow()
        )
        
        # Process PDFs with controlled concurrency
        semaphore = asyncio.Semaphore(3)  # Max 3 concurrent downloads
        results = []
        
        async def process_with_semaphore(pdf_url: str, index: int):
            async with semaphore:
                # Generate S3 key with timestamp
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                filename = os.path.basename(urlparse(pdf_url).path) or f"document_{index}.pdf"
                s3_key = f"documents/{timestamp}_{filename}"
                
                result = await download_and_upload_pdf_to_s3(pdf_url, s3_key)
                
                # Update processing status
                if result['status'] == 'success':
                    current_processing_status.processed += 1
                else:
                    current_processing_status.failed += 1
                
                current_processing_status.message = f"Processed {current_processing_status.processed + current_processing_status.failed}/{current_processing_status.total} PDFs"
                current_processing_status.timestamp = datetime.utcnow()
                
                return result
        
        # Process all PDFs
        tasks = [process_with_semaphore(url, i) for i, url in enumerate(pdf_links)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter successful results
        successful_results = [r for r in results if isinstance(r, dict) and r.get('status') == 'success']
        failed_results = [r for r in results if isinstance(r, dict) and r.get('status') == 'failed']
        
        # Update final status
        current_processing_status.status = "completed"
        current_processing_status.message = f"Processing completed: {len(successful_results)} successful, {len(failed_results)} failed"
        current_processing_status.timestamp = datetime.utcnow()
        
        # Trigger Bedrock Knowledge Base sync in background
        if successful_results:
            background_tasks.add_task(sync_bedrock_knowledge_base)
        
        return {
            "status": "completed",
            "processed": len(successful_results),
            "failed": len(failed_results),
            "total": len(pdf_links),
            "successful_uploads": successful_results,
            "message": f"Uploaded {len(successful_results)} PDFs to S3. Knowledge base sync started."
        }
        
    except Exception as e:
        current_processing_status = ProcessingStatus(
            status="failed",
            message=f"Processing failed: {str(e)}",
            processed=0,
            failed=0,
            total=0,
            timestamp=datetime.utcnow()
        )
        logger.error(f"Error in process_and_upload_pdfs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/processing-status")
async def get_processing_status():
    """Get current processing status"""
    if current_processing_status:
        return current_processing_status.dict()
    else:
        return {"status": "idle", "message": "No processing in progress"}

@app.post("/ask-question")
async def ask_question(request: QuestionRequest):
    """Ask a question using Bedrock Knowledge Base"""
    try:
        start_time = datetime.utcnow()
        
        if not BEDROCK_KNOWLEDGE_BASE_ID:
            # Fallback to simple response if Bedrock not configured
            return {
                "answer": "Bedrock Knowledge Base is not configured. Please upload and process some documents first.",
                "sources": [],
                "confidence": 0.0,
                "guardrails_applied": False,
                "model": "fallback",
                "processing_time": 0
            }
        
        # Query Bedrock Knowledge Base
        retrieve_response = bedrock_agent_client.retrieve(
            knowledgeBaseId=BEDROCK_KNOWLEDGE_BASE_ID,
            retrievalQuery={'text': request.question},
            retrievalConfiguration={
                'vectorSearchConfiguration': {
                    'numberOfResults': request.max_results
                }
            }
        )
        
        # Extract context from retrieved documents
        context_parts = []
        sources = []
        
        for result in retrieve_response.get('retrievalResults', []):
            content = result['content']['text']
            context_parts.append(content)
            
            # Extract source information
            location = result.get('location', {})
            s3_location = location.get('s3Location', {})
            
            sources.append({
                'content': content[:200] + '...' if len(content) > 200 else content,
                'score': result.get('score', 0),
                'source': s3_location.get('uri', 'Unknown'),
                'metadata': result.get('metadata', {})
            })
        
        # Generate answer using Bedrock
        context = "\n\n".join(context_parts[:3])  # Limit context size
        
        prompt = f"""Based on the following context from NCDHHS documents, please answer the question accurately and helpfully.

Context:
{context}

Question: {request.question}

Instructions:
- Provide a clear, accurate answer based only on the information in the context
- If the answer is not available in the context, clearly state that
- Be helpful and professional in your response
- Do not provide medical advice or personal health recommendations

Answer:"""
        
        # Prepare request for Bedrock
        request_body = {
            'messages': [{'role': 'user', 'content': prompt}],
            'max_tokens': 1000,
            'temperature': 0.1
        }
        
        # Call Bedrock with or without guardrails
        if request.use_guardrails and BEDROCK_GUARDRAIL_ID:
            response = bedrock_client.invoke_model(
                modelId=BEDROCK_PRIMARY_MODEL,
                body=json.dumps(request_body),
                guardrailIdentifier=BEDROCK_GUARDRAIL_ID,
                guardrailVersion=BEDROCK_GUARDRAIL_VERSION
            )
        else:
            response = bedrock_client.invoke_model(
                modelId=BEDROCK_PRIMARY_MODEL,
                body=json.dumps(request_body)
            )
        
        # Parse response
        response_body = json.loads(response['body'].read())
        answer = response_body.get('content', [{}])[0].get('text', 'No response generated')
        
        processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        return {
            "answer": answer,
            "sources": sources,
            "confidence": len(sources) / max(request.max_results, 1),
            "guardrails_applied": request.use_guardrails and bool(BEDROCK_GUARDRAIL_ID),
            "model": BEDROCK_PRIMARY_MODEL,
            "processing_time": processing_time,
            "documents_searched": len(sources)
        }
        
    except Exception as e:
        logger.error(f"Error in ask_question: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Question processing failed: {str(e)}")

@app.post("/sync-knowledge-base")
async def sync_knowledge_base_endpoint():
    """Manually trigger Bedrock Knowledge Base synchronization"""
    try:
        result = await sync_bedrock_knowledge_base()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/knowledge-base/status")
async def get_knowledge_base_status():
    """Get Bedrock Knowledge Base status"""
    try:
        if not BEDROCK_KNOWLEDGE_BASE_ID:
            return {"status": "not_configured", "message": "Knowledge Base ID not set"}
        
        # Get knowledge base info
        response = bedrock_agent_client.get_knowledge_base(
            knowledgeBaseId=BEDROCK_KNOWLEDGE_BASE_ID
        )
        
        return {
            "status": "configured",
            "knowledge_base_id": BEDROCK_KNOWLEDGE_BASE_ID,
            "name": response['knowledgeBase']['name'],
            "status_detail": response['knowledgeBase']['status'],
            "s3_bucket": S3_KNOWLEDGE_BASE_BUCKET
        }
        
    except Exception as e:
        logger.error(f"Error getting knowledge base status: {str(e)}")
        return {"status": "error", "message": str(e)}

@app.get("/documents")
async def list_documents():
    """List documents in S3 knowledge base bucket"""
    try:
        if not S3_KNOWLEDGE_BASE_BUCKET:
            return {"documents": [], "message": "S3 bucket not configured"}
        
        response = s3_client.list_objects_v2(
            Bucket=S3_KNOWLEDGE_BASE_BUCKET,
            Prefix='documents/'
        )
        
        documents = []
        for obj in response.get('Contents', []):
            # Get object metadata
            metadata_response = s3_client.head_object(
                Bucket=S3_KNOWLEDGE_BASE_BUCKET,
                Key=obj['Key']
            )
            
            documents.append({
                'key': obj['Key'],
                'filename': os.path.basename(obj['Key']),
                'size': obj['Size'],
                'last_modified': obj['LastModified'].isoformat(),
                'source_url': metadata_response.get('Metadata', {}).get('source_url', ''),
                'uploaded_at': metadata_response.get('Metadata', {}).get('uploaded_at', '')
            })
        
        return {
            "documents": documents,
            "count": len(documents),
            "bucket": S3_KNOWLEDGE_BASE_BUCKET
        }
        
    except Exception as e:
        logger.error(f"Error listing documents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check S3 access
        s3_status = "unknown"
        if S3_KNOWLEDGE_BASE_BUCKET:
            try:
                s3_client.head_bucket(Bucket=S3_KNOWLEDGE_BASE_BUCKET)
                s3_status = "healthy"
            except:
                s3_status = "error"
        
        # Check Bedrock access
        bedrock_status = "unknown"
        if BEDROCK_KNOWLEDGE_BASE_ID:
            try:
                bedrock_agent_client.get_knowledge_base(knowledgeBaseId=BEDROCK_KNOWLEDGE_BASE_ID)
                bedrock_status = "healthy"
            except:
                bedrock_status = "error"
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "3.0.0",
            "services": {
                "s3": s3_status,
                "bedrock": bedrock_status
            },
            "configuration": {
                "s3_bucket": S3_KNOWLEDGE_BASE_BUCKET,
                "knowledge_base_id": BEDROCK_KNOWLEDGE_BASE_ID,
                "primary_model": BEDROCK_PRIMARY_MODEL
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
