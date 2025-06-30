#!/usr/bin/env python3
"""
Patch to fix the OpenSearch index creation issue.
This script will modify the main application to ensure the index is created properly.
"""

import os

def patch_main_file():
    """Patch the main application file to fix index creation"""
    
    main_file_path = "/Users/dhanunjayudusurisetty/ncdhhs-pdf-qa/backend/main_with_opensearch.py"
    
    # Read the current file
    with open(main_file_path, 'r') as f:
        content = f.read()
    
    # Find the get_all_documents_from_opensearch function and patch it
    old_function = '''async def get_all_documents_from_opensearch() -> List[Dict[str, Any]]:
    """Get all documents from OpenSearch"""
    if not opensearch_client:
        logger.warning("OpenSearch not available - returning empty list")
        return []
    
    try:
        response = opensearch_client.search(
            index=OPENSEARCH_INDEX,
            body={
                "query": {"match_all": {}},
                "size": 1000,
                "_source": ["document_id", "title", "url", "pages", "processed_at"]
            }
        )
        
        documents = []
        for hit in response['hits']['hits']:
            doc_hit = hit['_source']
            # Only add unique documents (not chunks)
            if not any(doc['url'] == doc_hit['url'] for doc in documents):
                documents.append({
                    "id": doc_hit['document_id'],
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
        return []'''
    
    new_function = '''async def get_all_documents_from_opensearch() -> List[Dict[str, Any]]:
    """Get all documents from OpenSearch"""
    if not opensearch_client:
        logger.warning("OpenSearch not available - returning empty list")
        return []
    
    try:
        # Check if index exists, create if it doesn't
        if not opensearch_client.indices.exists(index=OPENSEARCH_INDEX):
            logger.warning(f"Index {OPENSEARCH_INDEX} does not exist, creating it...")
            await initialize_opensearch_index()
        
        response = opensearch_client.search(
            index=OPENSEARCH_INDEX,
            body={
                "query": {"match_all": {}},
                "size": 1000,
                "_source": ["document_id", "title", "url", "pages", "processed_at"]
            }
        )
        
        documents = []
        for hit in response['hits']['hits']:
            doc_hit = hit['_source']
            # Only add unique documents (not chunks)
            if not any(doc['url'] == doc_hit['url'] for doc in documents):
                documents.append({
                    "id": doc_hit['document_id'],
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
        return []'''
    
    # Replace the function
    if old_function in content:
        content = content.replace(old_function, new_function)
        print("Patched get_all_documents_from_opensearch function")
    else:
        print("Could not find the function to patch")
        return False
    
    # Also patch the store_document_chunks_in_opensearch function
    old_store_function = '''async def store_document_chunks_in_opensearch(document: Dict[str, Any], chunks: List[str], embeddings: List[List[float]]):
    """Store document chunks and embeddings in OpenSearch"""
    if not opensearch_client:
        logger.warning("OpenSearch not available - skipping storage")
        return False
    
    try:'''
    
    new_store_function = '''async def store_document_chunks_in_opensearch(document: Dict[str, Any], chunks: List[str], embeddings: List[List[float]]):
    """Store document chunks and embeddings in OpenSearch"""
    if not opensearch_client:
        logger.warning("OpenSearch not available - skipping storage")
        return False
    
    try:
        # Ensure index exists before storing
        if not opensearch_client.indices.exists(index=OPENSEARCH_INDEX):
            logger.warning(f"Index {OPENSEARCH_INDEX} does not exist, creating it...")
            await initialize_opensearch_index()'''
    
    if old_store_function in content:
        content = content.replace(old_store_function, new_store_function)
        print("Patched store_document_chunks_in_opensearch function")
    
    # Write the patched content back
    with open(main_file_path, 'w') as f:
        f.write(content)
    
    print("Successfully patched the main application file")
    return True

if __name__ == "__main__":
    print("Applying OpenSearch index fix...")
    if patch_main_file():
        print("Patch applied successfully!")
        print("Now rebuild and redeploy the Docker container.")
    else:
        print("Patch failed!")
