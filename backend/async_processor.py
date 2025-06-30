import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict
import boto3
from botocore.exceptions import ClientError

class AsyncPDFProcessor:
    def __init__(self, max_concurrent=5):
        self.max_concurrent = max_concurrent
        self.sqs = boto3.client('sqs')
        self.s3 = boto3.client('s3')
        
    async def process_pdfs_batch(self, pdf_urls: List[str]) -> Dict:
        """Process PDFs in batches with progress tracking"""
        
        # For large batches, use SQS for queue management
        if len(pdf_urls) > 10:
            return await self.queue_based_processing(pdf_urls)
        else:
            return await self.direct_processing(pdf_urls)
    
    async def queue_based_processing(self, pdf_urls: List[str]) -> Dict:
        """Use SQS for large batch processing"""
        queue_url = await self.create_processing_queue()
        
        # Send URLs to queue
        for url in pdf_urls:
            await self.send_to_queue(queue_url, url)
        
        return {
            "status": "queued",
            "total_pdfs": len(pdf_urls),
            "queue_url": queue_url,
            "estimated_time": f"{len(pdf_urls) * 2} minutes"
        }
    
    async def direct_processing(self, pdf_urls: List[str]) -> Dict:
        """Direct processing for smaller batches"""
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def process_single_pdf(url):
            async with semaphore:
                return await self.process_pdf_async(url)
        
        tasks = [process_single_pdf(url) for url in pdf_urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {
            "status": "completed",
            "processed": len([r for r in results if not isinstance(r, Exception)]),
            "failed": len([r for r in results if isinstance(r, Exception)]),
            "results": results
        }
