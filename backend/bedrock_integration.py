import boto3
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

class BedrockKnowledgeBaseManager:
    """Manage AWS Bedrock Knowledge Base and Guardrails for NCDHHS PDF Q&A"""
    
    def __init__(self, region_name: str = 'us-east-1'):
        self.region_name = region_name
        self.bedrock_agent_client = boto3.client('bedrock-agent', region_name=region_name)
        self.bedrock_client = boto3.client('bedrock-runtime', region_name=region_name)
        self.s3_client = boto3.client('s3', region_name=region_name)
        
        # Configuration
        self.knowledge_base_name = "ncdhhs-pdf-knowledge-base"
        self.guardrail_name = "ncdhhs-content-guardrail"
        self.s3_bucket = "ncdhhs-bedrock-knowledge-base"
        
    async def create_knowledge_base(self) -> Dict[str, Any]:
        """Create Bedrock Knowledge Base for PDF documents"""
        try:
            # First, create S3 bucket for knowledge base
            await self.create_s3_bucket()
            
            # Create the knowledge base
            response = self.bedrock_agent_client.create_knowledge_base(
                name=self.knowledge_base_name,
                description="Knowledge base for NCDHHS PDF documents and Q&A system",
                roleArn=await self.create_knowledge_base_role(),
                knowledgeBaseConfiguration={
                    'type': 'VECTOR',
                    'vectorKnowledgeBaseConfiguration': {
                        'embeddingModelArn': f'arn:aws:bedrock:{self.region_name}::foundation-model/amazon.titan-embed-text-v1',
                        'embeddingModelConfiguration': {
                            'bedrockEmbeddingModelConfiguration': {
                                'dimensions': 1536
                            }
                        }
                    }
                },
                storageConfiguration={
                    'type': 'OPENSEARCH_SERVERLESS',
                    'opensearchServerlessConfiguration': {
                        'collectionArn': await self.create_opensearch_collection(),
                        'vectorIndexName': 'ncdhhs-vector-index',
                        'fieldMapping': {
                            'vectorField': 'bedrock-knowledge-base-default-vector',
                            'textField': 'AMAZON_BEDROCK_TEXT_CHUNK',
                            'metadataField': 'AMAZON_BEDROCK_METADATA'
                        }
                    }
                }
            )
            
            knowledge_base_id = response['knowledgeBase']['knowledgeBaseId']
            logger.info(f"Created knowledge base: {knowledge_base_id}")
            
            # Create data source
            data_source_response = await self.create_data_source(knowledge_base_id)
            
            return {
                "knowledge_base_id": knowledge_base_id,
                "data_source_id": data_source_response['dataSource']['dataSourceId'],
                "status": "created"
            }
            
        except Exception as e:
            logger.error(f"Error creating knowledge base: {str(e)}")
            raise

    async def create_data_source(self, knowledge_base_id: str) -> Dict[str, Any]:
        """Create data source for the knowledge base"""
        try:
            response = self.bedrock_agent_client.create_data_source(
                knowledgeBaseId=knowledge_base_id,
                name="ncdhhs-pdf-data-source",
                description="Data source for NCDHHS PDF documents",
                dataSourceConfiguration={
                    'type': 'S3',
                    's3Configuration': {
                        'bucketArn': f'arn:aws:s3:::{self.s3_bucket}',
                        'inclusionPrefixes': ['documents/']
                    }
                },
                vectorIngestionConfiguration={
                    'chunkingConfiguration': {
                        'chunkingStrategy': 'FIXED_SIZE',
                        'fixedSizeChunkingConfiguration': {
                            'maxTokens': 512,
                            'overlapPercentage': 20
                        }
                    }
                }
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Error creating data source: {str(e)}")
            raise

    async def create_guardrail(self) -> Dict[str, Any]:
        """Create Bedrock Guardrail for content filtering"""
        try:
            response = self.bedrock_agent_client.create_guardrail(
                name=self.guardrail_name,
                description="Content guardrail for NCDHHS PDF Q&A system",
                topicPolicyConfig={
                    'topicsConfig': [
                        {
                            'name': 'Medical Information',
                            'definition': 'Discussions about medical procedures, diagnoses, or treatments',
                            'examples': [
                                'What medication should I take?',
                                'How do I treat this condition?',
                                'What are the symptoms of...'
                            ],
                            'type': 'DENY'
                        },
                        {
                            'name': 'Personal Health Information',
                            'definition': 'Requests for personal medical advice or diagnosis',
                            'examples': [
                                'What is wrong with me?',
                                'Should I see a doctor?',
                                'Am I sick?'
                            ],
                            'type': 'DENY'
                        }
                    ]
                },
                contentPolicyConfig={
                    'filtersConfig': [
                        {
                            'type': 'SEXUAL',
                            'inputStrength': 'HIGH',
                            'outputStrength': 'HIGH'
                        },
                        {
                            'type': 'VIOLENCE',
                            'inputStrength': 'HIGH',
                            'outputStrength': 'HIGH'
                        },
                        {
                            'type': 'HATE',
                            'inputStrength': 'HIGH',
                            'outputStrength': 'HIGH'
                        },
                        {
                            'type': 'INSULTS',
                            'inputStrength': 'MEDIUM',
                            'outputStrength': 'MEDIUM'
                        },
                        {
                            'type': 'MISCONDUCT',
                            'inputStrength': 'HIGH',
                            'outputStrength': 'HIGH'
                        }
                    ]
                },
                wordPolicyConfig={
                    'wordsConfig': [
                        {
                            'text': 'confidential'
                        },
                        {
                            'text': 'classified'
                        },
                        {
                            'text': 'internal use only'
                        }
                    ],
                    'managedWordListsConfig': [
                        {
                            'type': 'PROFANITY'
                        }
                    ]
                },
                sensitiveInformationPolicyConfig={
                    'piiEntitiesConfig': [
                        {
                            'type': 'EMAIL',
                            'action': 'BLOCK'
                        },
                        {
                            'type': 'PHONE',
                            'action': 'BLOCK'
                        },
                        {
                            'type': 'SSN',
                            'action': 'BLOCK'
                        },
                        {
                            'type': 'CREDIT_DEBIT_CARD_NUMBER',
                            'action': 'BLOCK'
                        }
                    ],
                    'regexesConfig': [
                        {
                            'name': 'Patient ID Pattern',
                            'description': 'Block patient ID patterns',
                            'pattern': r'P\d{6,8}',
                            'action': 'BLOCK'
                        }
                    ]
                },
                blockedInputMessaging="I cannot provide information on that topic. Please ask questions related to NCDHHS documents and services.",
                blockedOutputsMessaging="I cannot provide that type of information. Please ask questions about NCDHHS documents and services."
            )
            
            guardrail_id = response['guardrailId']
            guardrail_version = response['version']
            
            logger.info(f"Created guardrail: {guardrail_id} version {guardrail_version}")
            
            return {
                "guardrail_id": guardrail_id,
                "version": guardrail_version,
                "status": "created"
            }
            
        except Exception as e:
            logger.error(f"Error creating guardrail: {str(e)}")
            raise

    async def query_knowledge_base(self, question: str, knowledge_base_id: str, max_results: int = 5) -> Dict[str, Any]:
        """Query the Bedrock Knowledge Base"""
        try:
            response = self.bedrock_agent_client.retrieve(
                knowledgeBaseId=knowledge_base_id,
                retrievalQuery={
                    'text': question
                },
                retrievalConfiguration={
                    'vectorSearchConfiguration': {
                        'numberOfResults': max_results,
                        'overrideSearchType': 'HYBRID'
                    }
                }
            )
            
            # Extract relevant information
            results = []
            for result in response.get('retrievalResults', []):
                results.append({
                    'content': result['content']['text'],
                    'score': result['score'],
                    'location': result.get('location', {}),
                    'metadata': result.get('metadata', {})
                })
            
            return {
                'question': question,
                'results': results,
                'total_results': len(results)
            }
            
        except Exception as e:
            logger.error(f"Error querying knowledge base: {str(e)}")
            raise

    async def generate_answer_with_guardrails(self, question: str, context: str, guardrail_id: str, guardrail_version: str) -> Dict[str, Any]:
        """Generate answer using Bedrock with guardrails"""
        try:
            prompt = f"""
            Based on the following context from NCDHHS documents, please answer the question.
            
            Context: {context}
            
            Question: {question}
            
            Please provide a helpful and accurate answer based only on the information provided in the context.
            If the answer is not available in the context, please say so.
            """
            
            response = self.bedrock_client.invoke_model_with_response_stream(
                modelId='anthropic.claude-3-sonnet-20240229-v1:0',
                body=json.dumps({
                    'anthropic_version': 'bedrock-2023-05-31',
                    'max_tokens': 1000,
                    'messages': [
                        {
                            'role': 'user',
                            'content': prompt
                        }
                    ]
                }),
                guardrailIdentifier=guardrail_id,
                guardrailVersion=guardrail_version
            )
            
            # Process streaming response
            answer = ""
            for event in response['body']:
                chunk = json.loads(event['chunk']['bytes'])
                if chunk['type'] == 'content_block_delta':
                    answer += chunk['delta']['text']
            
            return {
                'question': question,
                'answer': answer,
                'guardrail_applied': True,
                'model': 'claude-3-sonnet'
            }
            
        except Exception as e:
            logger.error(f"Error generating answer with guardrails: {str(e)}")
            raise

    async def create_s3_bucket(self):
        """Create S3 bucket for knowledge base"""
        try:
            self.s3_client.create_bucket(
                Bucket=self.s3_bucket,
                CreateBucketConfiguration={
                    'LocationConstraint': self.region_name
                } if self.region_name != 'us-east-1' else {}
            )
            
            # Enable versioning
            self.s3_client.put_bucket_versioning(
                Bucket=self.s3_bucket,
                VersioningConfiguration={'Status': 'Enabled'}
            )
            
            logger.info(f"Created S3 bucket: {self.s3_bucket}")
            
        except Exception as e:
            if 'BucketAlreadyExists' not in str(e):
                logger.error(f"Error creating S3 bucket: {str(e)}")
                raise

    async def create_knowledge_base_role(self) -> str:
        """Create IAM role for knowledge base"""
        iam_client = boto3.client('iam')
        role_name = "BedrockKnowledgeBaseRole-NCDHHS"
        
        trust_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "Service": "bedrock.amazonaws.com"
                    },
                    "Action": "sts:AssumeRole"
                }
            ]
        }
        
        try:
            response = iam_client.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(trust_policy),
                Description="Role for Bedrock Knowledge Base access"
            )
            
            # Attach necessary policies
            policies = [
                "arn:aws:iam::aws:policy/AmazonBedrockFullAccess",
                "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess"
            ]
            
            for policy_arn in policies:
                iam_client.attach_role_policy(
                    RoleName=role_name,
                    PolicyArn=policy_arn
                )
            
            return response['Role']['Arn']
            
        except Exception as e:
            if 'EntityAlreadyExists' in str(e):
                response = iam_client.get_role(RoleName=role_name)
                return response['Role']['Arn']
            else:
                logger.error(f"Error creating IAM role: {str(e)}")
                raise

    async def create_opensearch_collection(self) -> str:
        """Create OpenSearch Serverless collection"""
        opensearch_client = boto3.client('opensearchserverless')
        collection_name = "ncdhhs-knowledge-base"
        
        try:
            response = opensearch_client.create_collection(
                name=collection_name,
                description="OpenSearch collection for NCDHHS Bedrock Knowledge Base",
                type='VECTORSEARCH'
            )
            
            return response['createCollectionDetail']['arn']
            
        except Exception as e:
            logger.error(f"Error creating OpenSearch collection: {str(e)}")
            raise

# Integration with main application
bedrock_manager = BedrockKnowledgeBaseManager()

async def setup_bedrock_infrastructure():
    """Setup complete Bedrock infrastructure"""
    try:
        logger.info("Setting up Bedrock infrastructure...")
        
        # Create knowledge base
        kb_result = await bedrock_manager.create_knowledge_base()
        logger.info(f"Knowledge base created: {kb_result}")
        
        # Create guardrail
        guardrail_result = await bedrock_manager.create_guardrail()
        logger.info(f"Guardrail created: {guardrail_result}")
        
        return {
            "knowledge_base": kb_result,
            "guardrail": guardrail_result,
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Error setting up Bedrock infrastructure: {str(e)}")
        raise
