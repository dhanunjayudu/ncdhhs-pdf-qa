from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import boto3
import json
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)

# Create router for Bedrock endpoints
bedrock_router = APIRouter(prefix="/bedrock", tags=["bedrock"])

# Pydantic models
class SearchDocumentsRequest(BaseModel):
    query: str
    search_mode: Optional[str] = "hybrid"  # "semantic", "keyword", "hybrid"
    max_results: Optional[int] = 5

class BedrockQuestionRequest(BaseModel):
    question: str
    search_results: Optional[List[Dict[str, Any]]] = []
    use_guardrails: Optional[bool] = True
    search_mode: Optional[str] = "hybrid"

class BedrockResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]
    confidence: Optional[float]
    guardrails_applied: bool
    model: str
    processing_time: int

# Initialize Bedrock clients
bedrock_client = boto3.client('bedrock-runtime', region_name=os.getenv('AWS_REGION', 'us-east-1'))
bedrock_agent_client = boto3.client('bedrock-agent', region_name=os.getenv('AWS_REGION', 'us-east-1'))

# Configuration from environment
KNOWLEDGE_BASE_ID = os.getenv('BEDROCK_KNOWLEDGE_BASE_ID')
GUARDRAIL_ID = os.getenv('BEDROCK_GUARDRAIL_ID')
GUARDRAIL_VERSION = os.getenv('BEDROCK_GUARDRAIL_VERSION', '1')

@bedrock_router.post("/search-documents")
async def search_documents(request: SearchDocumentsRequest):
    """Search documents using Bedrock Knowledge Base"""
    try:
        if not KNOWLEDGE_BASE_ID:
            raise HTTPException(status_code=500, detail="Knowledge Base not configured")
        
        start_time = datetime.now()
        
        # Configure search type based on mode
        search_type = "HYBRID"
        if request.search_mode == "semantic":
            search_type = "SEMANTIC"
        elif request.search_mode == "keyword":
            search_type = "HYBRID"  # Bedrock doesn't have pure keyword, use hybrid
        
        # Query the knowledge base
        response = bedrock_agent_client.retrieve(
            knowledgeBaseId=KNOWLEDGE_BASE_ID,
            retrievalQuery={
                'text': request.query
            },
            retrievalConfiguration={
                'vectorSearchConfiguration': {
                    'numberOfResults': request.max_results,
                    'overrideSearchType': search_type
                }
            }
        )
        
        # Process results
        results = []
        for result in response.get('retrievalResults', []):
            results.append({
                'content': result['content']['text'],
                'score': result['score'],
                'title': result.get('location', {}).get('s3Location', {}).get('uri', '').split('/')[-1],
                'metadata': result.get('metadata', {}),
                'location': result.get('location', {})
            })
        
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        return {
            'query': request.query,
            'results': results,
            'total_results': len(results),
            'search_mode': request.search_mode,
            'processing_time': processing_time
        }
        
    except Exception as e:
        logger.error(f"Error searching documents: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@bedrock_router.post("/ask-question-bedrock", response_model=BedrockResponse)
async def ask_question_bedrock(request: BedrockQuestionRequest):
    """Generate answer using Bedrock with guardrails"""
    try:
        start_time = datetime.now()
        
        # If no search results provided, search first
        if not request.search_results:
            search_request = SearchDocumentsRequest(
                query=request.question,
                search_mode=request.search_mode,
                max_results=5
            )
            search_response = await search_documents(search_request)
            search_results = search_response['results']
        else:
            search_results = request.search_results
        
        # Build context from search results
        context_parts = []
        sources = []
        
        for i, result in enumerate(search_results[:5]):  # Limit to top 5 results
            context_parts.append(f"Document {i+1}: {result['content']}")
            sources.append({
                'title': result.get('title', f'Document {i+1}'),
                'content': result['content'][:200] + '...' if len(result['content']) > 200 else result['content'],
                'score': result.get('score', 0),
                'metadata': result.get('metadata', {})
            })
        
        context = "\n\n".join(context_parts)
        
        # Create prompt
        prompt = f"""
Based on the following context from NCDHHS documents, please answer the question accurately and helpfully.

Context:
{context}

Question: {request.question}

Instructions:
- Provide a clear, accurate answer based only on the information in the context
- If the answer is not available in the context, clearly state that
- Be helpful and professional in your response
- Cite specific information from the documents when relevant
- Do not provide medical advice or personal health recommendations

Answer:"""
        
        # Prepare request body
        request_body = {
            'anthropic_version': 'bedrock-2023-05-31',
            'max_tokens': 1000,
            'messages': [
                {
                    'role': 'user',
                    'content': prompt
                }
            ],
            'temperature': 0.1,
            'top_p': 0.9
        }
        
        # Make request with or without guardrails
        if request.use_guardrails and GUARDRAIL_ID:
            response = bedrock_client.invoke_model_with_response_stream(
                modelId='anthropic.claude-3-sonnet-20240229-v1:0',
                body=json.dumps(request_body),
                guardrailIdentifier=GUARDRAIL_ID,
                guardrailVersion=GUARDRAIL_VERSION
            )
            guardrails_applied = True
        else:
            response = bedrock_client.invoke_model_with_response_stream(
                modelId='anthropic.claude-3-sonnet-20240229-v1:0',
                body=json.dumps(request_body)
            )
            guardrails_applied = False
        
        # Process streaming response
        answer = ""
        for event in response['body']:
            chunk = json.loads(event['chunk']['bytes'])
            if chunk['type'] == 'content_block_delta':
                answer += chunk['delta']['text']
        
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        # Calculate confidence based on search scores
        confidence = 0.0
        if sources:
            confidence = sum(source.get('score', 0) for source in sources) / len(sources)
        
        return BedrockResponse(
            answer=answer.strip(),
            sources=sources,
            confidence=confidence,
            guardrails_applied=guardrails_applied,
            model='claude-3-sonnet',
            processing_time=processing_time
        )
        
    except Exception as e:
        logger.error(f"Error generating answer with Bedrock: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Answer generation failed: {str(e)}")

@bedrock_router.get("/knowledge-base/status")
async def get_knowledge_base_status():
    """Get knowledge base status and statistics"""
    try:
        if not KNOWLEDGE_BASE_ID:
            return {"status": "not_configured", "message": "Knowledge Base ID not set"}
        
        # Get knowledge base details
        response = bedrock_agent_client.get_knowledge_base(
            knowledgeBaseId=KNOWLEDGE_BASE_ID
        )
        
        kb_info = response['knowledgeBase']
        
        # Get data sources
        data_sources_response = bedrock_agent_client.list_data_sources(
            knowledgeBaseId=KNOWLEDGE_BASE_ID
        )
        
        data_sources = []
        for ds in data_sources_response.get('dataSourceSummaries', []):
            data_sources.append({
                'id': ds['dataSourceId'],
                'name': ds['name'],
                'status': ds['status'],
                'updated_at': ds.get('updatedAt', '').isoformat() if ds.get('updatedAt') else None
            })
        
        return {
            'status': 'configured',
            'knowledge_base': {
                'id': kb_info['knowledgeBaseId'],
                'name': kb_info['name'],
                'status': kb_info['status'],
                'created_at': kb_info.get('createdAt', '').isoformat() if kb_info.get('createdAt') else None,
                'updated_at': kb_info.get('updatedAt', '').isoformat() if kb_info.get('updatedAt') else None
            },
            'data_sources': data_sources,
            'guardrail': {
                'id': GUARDRAIL_ID,
                'version': GUARDRAIL_VERSION,
                'enabled': bool(GUARDRAIL_ID)
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting knowledge base status: {str(e)}")
        return {
            'status': 'error',
            'message': str(e)
        }

@bedrock_router.post("/knowledge-base/sync")
async def sync_knowledge_base():
    """Trigger knowledge base synchronization"""
    try:
        if not KNOWLEDGE_BASE_ID:
            raise HTTPException(status_code=500, detail="Knowledge Base not configured")
        
        # Get data sources
        data_sources_response = bedrock_agent_client.list_data_sources(
            knowledgeBaseId=KNOWLEDGE_BASE_ID
        )
        
        sync_jobs = []
        for ds in data_sources_response.get('dataSourceSummaries', []):
            # Start ingestion job
            job_response = bedrock_agent_client.start_ingestion_job(
                knowledgeBaseId=KNOWLEDGE_BASE_ID,
                dataSourceId=ds['dataSourceId']
            )
            
            sync_jobs.append({
                'data_source_id': ds['dataSourceId'],
                'data_source_name': ds['name'],
                'job_id': job_response['ingestionJob']['ingestionJobId'],
                'status': job_response['ingestionJob']['status']
            })
        
        return {
            'message': f'Started {len(sync_jobs)} synchronization jobs',
            'jobs': sync_jobs
        }
        
    except Exception as e:
        logger.error(f"Error syncing knowledge base: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")

@bedrock_router.get("/models/available")
async def get_available_models():
    """Get list of available Bedrock models"""
    try:
        response = bedrock_client.list_foundation_models()
        
        models = []
        for model in response.get('modelSummaries', []):
            if model.get('responseStreamingSupported', False):  # Only streaming models
                models.append({
                    'id': model['modelId'],
                    'name': model['modelName'],
                    'provider': model['providerName'],
                    'input_modalities': model.get('inputModalities', []),
                    'output_modalities': model.get('outputModalities', [])
                })
        
        return {
            'models': models,
            'total': len(models)
        }
        
    except Exception as e:
        logger.error(f"Error getting available models: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get models: {str(e)}")

# Health check for Bedrock services
@bedrock_router.get("/health")
async def bedrock_health_check():
    """Health check for Bedrock integration"""
    try:
        health_status = {
            'bedrock_runtime': False,
            'bedrock_agent': False,
            'knowledge_base': False,
            'guardrail': False
        }
        
        # Test Bedrock Runtime
        try:
            bedrock_client.list_foundation_models()
            health_status['bedrock_runtime'] = True
        except:
            pass
        
        # Test Bedrock Agent
        try:
            if KNOWLEDGE_BASE_ID:
                bedrock_agent_client.get_knowledge_base(knowledgeBaseId=KNOWLEDGE_BASE_ID)
                health_status['knowledge_base'] = True
        except:
            pass
        
        # Test Guardrail
        if GUARDRAIL_ID:
            try:
                bedrock_agent_client.get_guardrail(
                    guardrailIdentifier=GUARDRAIL_ID,
                    guardrailVersion=GUARDRAIL_VERSION
                )
                health_status['guardrail'] = True
            except:
                pass
        
        overall_health = all(health_status.values())
        
        return {
            'status': 'healthy' if overall_health else 'degraded',
            'services': health_status,
            'configuration': {
                'knowledge_base_id': KNOWLEDGE_BASE_ID,
                'guardrail_id': GUARDRAIL_ID,
                'guardrail_version': GUARDRAIL_VERSION
            }
        }
        
    except Exception as e:
        logger.error(f"Bedrock health check failed: {str(e)}")
        return {
            'status': 'unhealthy',
            'error': str(e)
        }
