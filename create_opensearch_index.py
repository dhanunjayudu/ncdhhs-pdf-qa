#!/usr/bin/env python3
"""
Script to manually create the OpenSearch index for the NC DHHS PDF Q&A system.
This addresses the index_not_found_exception error.
"""

import boto3
import json
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth

# Configuration
AWS_REGION = "us-east-1"
OPENSEARCH_ENDPOINT = "vpc-ncdhhs-pdf-qa-opensearch-kuqxszpumb6yail7yttzdlfnvq.us-east-1.es.amazonaws.com"
OPENSEARCH_INDEX = "ncdhhs-documents"

def create_opensearch_index():
    """Create the OpenSearch index with proper mapping for vector search"""
    
    # Get AWS credentials
    session = boto3.Session()
    credentials = session.get_credentials()
    
    # Create AWS auth
    awsauth = AWS4Auth(
        credentials.access_key,
        credentials.secret_key,
        AWS_REGION,
        'es',
        session_token=credentials.token
    )
    
    # Initialize OpenSearch client
    opensearch_client = OpenSearch(
        hosts=[{'host': OPENSEARCH_ENDPOINT, 'port': 443}],
        http_auth=awsauth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        timeout=60
    )
    
    try:
        # Check if index exists
        if opensearch_client.indices.exists(index=OPENSEARCH_INDEX):
            print(f"Index '{OPENSEARCH_INDEX}' already exists")
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
        
        print(f"Successfully created OpenSearch index '{OPENSEARCH_INDEX}'")
        print(f"Response: {response}")
        return True
        
    except Exception as e:
        print(f"Error creating OpenSearch index: {str(e)}")
        return False

if __name__ == "__main__":
    print("Creating OpenSearch index for NC DHHS PDF Q&A system...")
    success = create_opensearch_index()
    if success:
        print("Index creation completed successfully!")
    else:
        print("Index creation failed!")
