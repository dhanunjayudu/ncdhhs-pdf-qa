from fastapi import WebSocket
import asyncio
import json
from typing import List

class ProgressiveProcessor:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    async def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def send_progress(self, message: dict):
        """Send progress updates to all connected clients"""
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except:
                await self.disconnect(connection)
    
    async def process_with_progress(self, pdf_urls: List[str]):
        """Process PDFs with real-time progress updates"""
        total = len(pdf_urls)
        processed = 0
        
        await self.send_progress({
            "type": "started",
            "total": total,
            "message": f"Starting to process {total} PDFs..."
        })
        
        for i, url in enumerate(pdf_urls):
            try:
                # Process individual PDF
                result = await self.process_single_pdf(url)
                processed += 1
                
                await self.send_progress({
                    "type": "progress",
                    "current": i + 1,
                    "total": total,
                    "percentage": ((i + 1) / total) * 100,
                    "message": f"Processed {i + 1}/{total} PDFs",
                    "latest_pdf": url
                })
                
                # Allow other tasks to run
                await asyncio.sleep(0.1)
                
            except Exception as e:
                await self.send_progress({
                    "type": "error",
                    "message": f"Failed to process {url}: {str(e)}"
                })
        
        await self.send_progress({
            "type": "completed",
            "processed": processed,
            "total": total,
            "message": f"Completed processing {processed}/{total} PDFs"
        })
