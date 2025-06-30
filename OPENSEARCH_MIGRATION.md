# OpenSearch Vector Database Migration

This document outlines the migration from in-memory storage to Amazon OpenSearch for vector database functionality in the NC DHHS PDF Q&A system.

## Overview

The system has been enhanced to use **Amazon OpenSearch** as a persistent vector database, replacing the previous in-memory storage approach. This provides:

- **Persistent storage** of document embeddings
- **Scalable vector search** with HNSW algorithm
- **Better performance** for large document collections
- **Advanced search capabilities** with semantic similarity
- **High availability** and durability

## Architecture Changes

### Before (In-Memory)
```
FastAPI App → In-Memory Lists → Cosine Similarity → Results
```

### After (OpenSearch)
```
FastAPI App → OpenSearch Cluster → Vector Search (HNSW) → Results
```

## Key Components

### 1. OpenSearch Domain
- **Instance Type**: `t3.small.search` (configurable)
- **Storage**: 20GB EBS GP3 volume
- **Security**: VPC-based with security groups
- **Encryption**: At-rest and in-transit
- **Authentication**: IAM-based access control

### 2. Vector Configuration
- **Embedding Dimension**: 1024 (Amazon Titan Embed Text v2)
- **Algorithm**: HNSW (Hierarchical Navigable Small World)
- **Distance Metric**: Cosine similarity
- **Index Settings**: Optimized for search performance

### 3. Document Processing
- **Chunking**: Intelligent text splitting with overlap
- **Embedding**: AWS Bedrock Titan v2 embeddings
- **Storage**: Bulk indexing for efficiency
- **Metadata**: Title, URL, page info, timestamps

## Files Changed/Added

### New Files
- `backend/main_with_opensearch.py` - OpenSearch-enabled application
- `backend/requirements_opensearch.txt` - Updated dependencies
- `backend/Dockerfile_opensearch` - OpenSearch-compatible container
- `aws/opensearch.tf` - OpenSearch infrastructure
- `deploy_opensearch.sh` - Deployment script
- `OPENSEARCH_MIGRATION.md` - This documentation

### Modified Files
- `aws/variables.tf` - Added OpenSearch variables
- `aws/iam.tf` - Added OpenSearch permissions
- `aws/ecs.tf` - Added OpenSearch environment variables
- `aws/outputs.tf` - Added OpenSearch outputs

## Deployment

### Prerequisites
- AWS CLI configured
- Docker installed
- Terraform installed
- Sufficient AWS permissions

### Quick Deployment
```bash
./deploy_opensearch.sh
```

### Manual Deployment
```bash
# 1. Build and push Docker image
cd backend
docker build -f Dockerfile_opensearch -t ncdhhs-pdf-qa-opensearch .

# 2. Deploy infrastructure
cd ../aws
terraform init
terraform plan
terraform apply

# 3. Update ECS service (automatic)
```

## Configuration

### Environment Variables
```bash
OPENSEARCH_ENDPOINT=https://your-domain.us-east-1.es.amazonaws.com
OPENSEARCH_INDEX=ncdhhs-documents
AWS_REGION=us-east-1
```

### Terraform Variables
```hcl
opensearch_instance_type   = "t3.small.search"
opensearch_instance_count  = 1
opensearch_volume_size     = 20
```

## API Changes

### New Endpoints
All existing endpoints remain the same, but now use OpenSearch backend:

- `GET /health` - Shows OpenSearch availability
- `POST /process-pdf-batch` - Stores in OpenSearch
- `POST /ask` - Searches OpenSearch
- `GET /documents` - Retrieves from OpenSearch
- `DELETE /documents` - Clears OpenSearch index

### Response Enhancements
```json
{
  "question": "What is CPS assessment?",
  "answer": "Based on the NC DHHS documents...",
  "sources": [
    {
      "title": "CPS Assessments Manual",
      "url": "https://...",
      "pages": 98,
      "relevance_score": 0.89
    }
  ]
}
```

## Performance Improvements

### Search Performance
- **Vector Search**: HNSW algorithm for fast approximate nearest neighbor search
- **Bulk Operations**: Efficient document indexing
- **Caching**: OpenSearch internal caching
- **Scaling**: Horizontal scaling capability

### Memory Usage
- **Reduced Memory**: No in-memory storage of embeddings
- **Efficient Processing**: Streaming document processing
- **Resource Optimization**: Better container resource utilization

## Monitoring

### Health Checks
```bash
# Application health
curl http://your-alb-url/health

# OpenSearch cluster health
aws es describe-elasticsearch-domain --domain-name ncdhhs-pdf-qa-opensearch
```

### CloudWatch Metrics
- OpenSearch cluster metrics
- ECS task performance
- Application logs

### Kibana Dashboard
Access via OpenSearch Kibana endpoint for:
- Index statistics
- Search performance
- Document analysis

## Cost Considerations

### OpenSearch Costs
- **Instance**: ~$25/month for t3.small.search
- **Storage**: ~$2/month for 20GB
- **Data Transfer**: Minimal within VPC

### Comparison
- **Before**: Higher memory requirements, scaling limitations
- **After**: Fixed OpenSearch cost, better scaling economics

## Migration Strategy

### Zero-Downtime Migration
1. Deploy OpenSearch infrastructure
2. Update application with fallback logic
3. Migrate existing documents
4. Switch to OpenSearch backend
5. Remove in-memory storage

### Rollback Plan
1. Keep original `main.py` as backup
2. Switch ECS task definition
3. Update environment variables
4. Restart services

## Troubleshooting

### Common Issues

#### OpenSearch Connection
```bash
# Check security groups
aws ec2 describe-security-groups --group-ids sg-xxx

# Check IAM permissions
aws iam simulate-principal-policy --policy-source-arn arn:aws:iam::xxx:role/xxx
```

#### Index Issues
```bash
# Check index health
curl -X GET "https://your-endpoint/_cat/indices?v"

# Recreate index
curl -X DELETE "https://your-endpoint/ncdhhs-documents"
```

#### Performance Issues
```bash
# Check cluster stats
curl -X GET "https://your-endpoint/_cluster/stats"

# Monitor search performance
curl -X GET "https://your-endpoint/_cat/nodes?v"
```

## Security

### Network Security
- VPC-only access
- Security group restrictions
- No public internet access

### Data Security
- Encryption at rest (AES-256)
- Encryption in transit (TLS 1.2+)
- IAM-based authentication

### Access Control
- Fine-grained IAM policies
- Service-to-service authentication
- No anonymous access

## Future Enhancements

### Potential Improvements
1. **Multi-AZ Deployment** for high availability
2. **Index Templates** for better document management
3. **Custom Analyzers** for domain-specific text processing
4. **Alerting** for operational monitoring
5. **Backup/Restore** automation

### Scaling Options
1. **Vertical Scaling**: Larger instance types
2. **Horizontal Scaling**: Multiple nodes
3. **Storage Scaling**: Larger EBS volumes
4. **Read Replicas**: For read-heavy workloads

## Support

### Documentation
- [Amazon OpenSearch Service](https://docs.aws.amazon.com/opensearch-service/)
- [OpenSearch Python Client](https://opensearch.org/docs/latest/clients/python/)
- [Vector Search Guide](https://opensearch.org/docs/latest/search-plugins/knn/)

### Monitoring
- CloudWatch dashboards
- OpenSearch logs
- Application metrics

This migration significantly enhances the system's capabilities while maintaining backward compatibility and improving performance for the NC DHHS PDF Q&A use case.
