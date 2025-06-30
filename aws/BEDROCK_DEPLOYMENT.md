# AWS Bedrock Integration Deployment Guide

This guide walks you through deploying the enhanced NCDHHS PDF Q&A system with AWS Bedrock Knowledge Base and Guardrails.

## 🚀 Quick Start

```bash
cd aws/
./deploy-bedrock.sh
```

## 📋 Prerequisites

### Required Tools
- [Terraform](https://www.terraform.io/downloads.html) >= 1.0
- [AWS CLI](https://aws.amazon.com/cli/) configured with appropriate permissions
- [Git](https://git-scm.com/) for version control

### AWS Permissions Required
Your AWS credentials need the following permissions:
- **Bedrock**: Full access to create Knowledge Bases and Guardrails
- **OpenSearch Serverless**: Create and manage collections
- **S3**: Create and manage buckets
- **IAM**: Create roles and policies
- **ECS**: Update task definitions and services
- **CloudWatch**: Create dashboards and log groups

## 🏗️ Infrastructure Overview

The Terraform configuration creates:

### 🧠 **Bedrock Components**
- **Knowledge Base**: Vector database for PDF documents
- **Guardrails**: Content filtering for safe AI responses
- **Data Source**: S3-based document ingestion
- **OpenSearch Serverless**: Vector storage backend

### 🔐 **Security Components**
- **IAM Roles**: Secure access between services
- **Access Policies**: Fine-grained permissions
- **Encryption**: Data encryption at rest and in transit

### 📊 **Monitoring Components**
- **CloudWatch Dashboard**: Bedrock usage metrics
- **Log Groups**: Application and service logs

## 🔧 Deployment Steps

### 1. **Initialize and Plan**
```bash
cd aws/
terraform init
terraform plan
```

### 2. **Deploy Infrastructure**
```bash
terraform apply
```

Or use the automated script:
```bash
./deploy-bedrock.sh
```

### 3. **Enable Bedrock Models**
After deployment, enable model access in the AWS Console:

1. Go to [Bedrock Console](https://console.aws.amazon.com/bedrock/)
2. Navigate to "Model access" in the left sidebar
3. Enable the following models:
   - `anthropic.claude-3-sonnet-20240229-v1:0`
   - `anthropic.claude-3-haiku-20240307-v1:0`
   - `amazon.titan-embed-text-v1`

### 4. **Upload Documents**
Upload your PDF documents to the Knowledge Base S3 bucket:

```bash
# Get bucket name from Terraform output
BUCKET_NAME=$(terraform output -raw bedrock_s3_bucket)

# Upload documents
aws s3 cp your-documents/ s3://$BUCKET_NAME/documents/ --recursive
```

### 5. **Sync Knowledge Base**
Trigger document ingestion:

```bash
# Get configuration from Terraform outputs
KB_ID=$(terraform output -raw bedrock_knowledge_base_id)
DS_ID=$(terraform output -raw bedrock_data_source_id)

# Start ingestion job
aws bedrock-agent start-ingestion-job \
  --knowledge-base-id $KB_ID \
  --data-source-id $DS_ID \
  --region us-east-1
```

### 6. **Update Backend Application**
The ECS task definition is automatically updated with Bedrock environment variables:

- `BEDROCK_KNOWLEDGE_BASE_ID`
- `BEDROCK_DATA_SOURCE_ID`
- `BEDROCK_GUARDRAIL_ID`
- `BEDROCK_GUARDRAIL_VERSION`
- `S3_KNOWLEDGE_BASE_BUCKET`
- `OPENSEARCH_COLLECTION_ARN`

## 📊 Monitoring and Management

### CloudWatch Dashboard
Access the Bedrock monitoring dashboard:
```bash
# Get dashboard URL
echo "https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=$(terraform output -raw project_name)-bedrock-monitoring"
```

### Knowledge Base Management
```bash
# Check ingestion job status
aws bedrock-agent get-ingestion-job \
  --knowledge-base-id $KB_ID \
  --data-source-id $DS_ID \
  --ingestion-job-id $JOB_ID

# List all ingestion jobs
aws bedrock-agent list-ingestion-jobs \
  --knowledge-base-id $KB_ID \
  --data-source-id $DS_ID
```

## 🧪 Testing the Enhanced Features

### 1. **Test Knowledge Base Query**
```bash
aws bedrock-agent retrieve \
  --knowledge-base-id $KB_ID \
  --retrieval-query '{"text": "What services are available?"}' \
  --retrieval-configuration '{"vectorSearchConfiguration": {"numberOfResults": 5}}'
```

### 2. **Test Guardrails**
The guardrails automatically filter:
- Medical advice requests
- Personal health information
- Inappropriate content
- PII data

### 3. **Frontend Testing**
1. Visit your application URL
2. Process some PDFs using the enhanced processor
3. Try the AI-powered Q&A with different search modes
4. Verify source attribution and confidence scores

## 🔍 Troubleshooting

### Common Issues

#### **Model Access Not Enabled**
```
Error: AccessDeniedException: You don't have access to the model
```
**Solution**: Enable model access in Bedrock Console

#### **Knowledge Base Empty**
```
Error: No relevant documents found
```
**Solution**: 
1. Upload documents to S3 bucket
2. Run ingestion job
3. Wait for completion

#### **Guardrail Blocking Responses**
```
Response: "I cannot provide information on that topic"
```
**Solution**: This is expected behavior for filtered content

#### **OpenSearch Collection Not Ready**
```
Error: Collection not in ACTIVE state
```
**Solution**: Wait for collection to become active (can take 10-15 minutes)

### Debug Commands
```bash
# Check Terraform state
terraform show

# Validate configuration
terraform validate

# Check AWS resources
aws bedrock-agent get-knowledge-base --knowledge-base-id $KB_ID
aws opensearchserverless list-collections
aws s3 ls s3://$BUCKET_NAME/documents/
```

## 💰 Cost Optimization

### Bedrock Pricing
- **Knowledge Base**: $0.10 per GB stored per month
- **Claude 3 Sonnet**: $3.00 per 1M input tokens, $15.00 per 1M output tokens
- **Claude 3 Haiku**: $0.25 per 1M input tokens, $1.25 per 1M output tokens
- **Titan Embeddings**: $0.0001 per 1K tokens

### OpenSearch Serverless
- **Vector Search**: $0.24 per OCU-hour
- **Storage**: $1.50 per GB-month

### Cost Control Tips
1. Use Claude 3 Haiku for simple queries
2. Implement caching for repeated questions
3. Monitor usage via CloudWatch
4. Set up billing alerts

## 🔄 Updates and Maintenance

### Updating Documents
```bash
# Upload new documents
aws s3 cp new-documents/ s3://$BUCKET_NAME/documents/ --recursive

# Trigger re-ingestion
aws bedrock-agent start-ingestion-job \
  --knowledge-base-id $KB_ID \
  --data-source-id $DS_ID
```

### Updating Guardrails
```bash
# Update guardrail configuration
terraform apply -target=aws_bedrock_guardrail.ncdhhs_content_filter
```

### Scaling Considerations
- OpenSearch Serverless auto-scales
- Bedrock has built-in rate limiting
- Monitor CloudWatch metrics for usage patterns

## 📚 Additional Resources

- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [OpenSearch Serverless Guide](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/serverless.html)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)

## 🆘 Support

For issues with this deployment:
1. Check the troubleshooting section above
2. Review CloudWatch logs
3. Validate Terraform configuration
4. Check AWS service status

---

**Note**: This deployment creates AWS resources that incur costs. Make sure to understand the pricing model and monitor your usage.
