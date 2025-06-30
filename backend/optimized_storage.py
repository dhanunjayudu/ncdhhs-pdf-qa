import boto3
import json
from typing import Dict, List
from datetime import datetime

class OptimizedStorageManager:
    """
    Optimized storage strategy:
    1. S3: Store original PDFs + metadata
    2. OpenSearch: Store searchable text chunks + embeddings
    3. No redundant .txt files
    """
    
    def __init__(self):
        self.s3 = boto3.client('s3')
        self.opensearch = boto3.client('opensearch')
        self.bucket_name = "ncdhhs-pdf-documents"
    
    async def store_document_optimized(self, pdf_url: str, content: str, metadata: Dict):
        """Optimized storage without redundancy"""
        
        # 1. Store original PDF in S3 (if needed for reference)
        pdf_key = f"originals/{metadata['doc_id']}.pdf"
        
        # 2. Create document chunks for better search
        chunks = self.create_text_chunks(content, chunk_size=1000)
        
        # 3. Store metadata in S3 as JSON
        metadata_key = f"metadata/{metadata['doc_id']}.json"
        await self.store_metadata(metadata_key, {
            **metadata,
            "chunks_count": len(chunks),
            "processed_at": datetime.utcnow().isoformat(),
            "source_url": pdf_url
        })
        
        # 4. Index chunks in OpenSearch with embeddings
        for i, chunk in enumerate(chunks):
            await self.index_chunk_in_opensearch({
                "doc_id": metadata['doc_id'],
                "chunk_id": f"{metadata['doc_id']}_chunk_{i}",
                "content": chunk,
                "metadata": metadata,
                "chunk_index": i
            })
        
        return {
            "doc_id": metadata['doc_id'],
            "chunks_stored": len(chunks),
            "s3_metadata_key": metadata_key
        }
    
    def create_text_chunks(self, text: str, chunk_size: int = 1000) -> List[str]:
        """Create overlapping text chunks for better search"""
        words = text.split()
        chunks = []
        
        for i in range(0, len(words), chunk_size - 100):  # 100 word overlap
            chunk = ' '.join(words[i:i + chunk_size])
            chunks.append(chunk)
        
        return chunks

# Alternative: Use only OpenSearch (recommended)
class OpenSearchOnlyStorage:
    """
    Simplified approach: Store everything in OpenSearch
    - Original PDF content as base64 (if needed)
    - Extracted text in searchable fields
    - Metadata in structured fields
    """
    
    def __init__(self):
        self.opensearch_client = self.get_opensearch_client()
    
    async def store_document_simple(self, pdf_url: str, content: str, metadata: Dict):
        """Store everything in OpenSearch - no S3 needed"""
        
        doc = {
            "doc_id": metadata['doc_id'],
            "source_url": pdf_url,
            "title": metadata.get('title', ''),
            "content": content,
            "content_length": len(content),
            "processed_at": datetime.utcnow().isoformat(),
            "metadata": metadata,
            # Create searchable chunks within the same document
            "chunks": self.create_searchable_chunks(content)
        }
        
        # Single storage operation
        response = await self.opensearch_client.index(
            index="ncdhhs-documents",
            id=metadata['doc_id'],
            body=doc
        )
        
        return response
