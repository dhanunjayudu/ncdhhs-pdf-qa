from fastapi import FastAPI, BackgroundTasks, WebSocket
from pydantic import BaseModel
import asyncio
from typing import List
import uuid

app = FastAPI()

class ProcessingJob:
    def __init__(self, job_id: str, total_pdfs: int):
        self.job_id = job_id
        self.total_pdfs = total_pdfs
        self.processed = 0
        self.status = "queued"
        self.results = []

# In-memory job tracking (use Redis in production)
active_jobs = {}

@app.post("/process-website-async")
async def process_website_async(
    request: dict, 
    background_tasks: BackgroundTasks
):
    """Start async processing for large PDF batches"""
    
    # Extract PDF links first (quick operation)
    pdf_links = await extract_pdf_links(request["url"])
    
    if len(pdf_links) > 10:
        # Use background processing for large batches
        job_id = str(uuid.uuid4())
        job = ProcessingJob(job_id, len(pdf_links))
        active_jobs[job_id] = job
        
        # Start background processing
        background_tasks.add_task(process_pdfs_background, job_id, pdf_links)
        
        return {
            "job_id": job_id,
            "status": "queued",
            "total_pdfs": len(pdf_links),
            "estimated_time_minutes": len(pdf_links) * 2,
            "progress_endpoint": f"/job-status/{job_id}"
        }
    else:
        # Process small batches directly
        results = await process_pdfs_direct(pdf_links)
        return {
            "status": "completed",
            "results": results
        }

@app.get("/job-status/{job_id}")
async def get_job_status(job_id: str):
    """Get processing job status"""
    if job_id not in active_jobs:
        return {"error": "Job not found"}
    
    job = active_jobs[job_id]
    return {
        "job_id": job_id,
        "status": job.status,
        "progress": {
            "processed": job.processed,
            "total": job.total_pdfs,
            "percentage": (job.processed / job.total_pdfs) * 100
        },
        "results": job.results
    }

@app.websocket("/ws/progress/{job_id}")
async def websocket_progress(websocket: WebSocket, job_id: str):
    """Real-time progress updates via WebSocket"""
    await websocket.accept()
    
    while job_id in active_jobs:
        job = active_jobs[job_id]
        await websocket.send_json({
            "processed": job.processed,
            "total": job.total_pdfs,
            "status": job.status,
            "percentage": (job.processed / job.total_pdfs) * 100
        })
        
        if job.status == "completed":
            break
            
        await asyncio.sleep(2)  # Update every 2 seconds

async def process_pdfs_background(job_id: str, pdf_urls: List[str]):
    """Background processing with progress tracking"""
    job = active_jobs[job_id]
    job.status = "processing"
    
    for i, url in enumerate(pdf_urls):
        try:
            # Process single PDF (optimized storage)
            result = await process_single_pdf_optimized(url)
            job.results.append(result)
            job.processed += 1
            
        except Exception as e:
            job.results.append({"url": url, "error": str(e)})
        
        # Small delay to prevent overwhelming the system
        await asyncio.sleep(0.5)
    
    job.status = "completed"
