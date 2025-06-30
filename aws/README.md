# NC DHHS PDF Q&A - AWS Infrastructure

This directory contains Terraform configuration for deploying the NC DHHS PDF Q&A application to AWS with AI-powered document processing using Amazon Bedrock.

## Architecture

The infrastructure includes:

- **VPC** with public and private subnets across 2 AZs
- **ECS Fargate** cluster for running the containerized application
- **Application Load Balancer** with extended timeout for PDF processing
- **ElastiCache Redis** for caching
- **S3 bucket** for document storage
- **ECR repository** for container images
- **IAM roles** with Bedrock and S3 permissions
- **CloudWatch** for logging and monitoring
- **Amazon Bedrock** integration for AI-powered Q&A

## Prerequisites

1. **AWS CLI** configured with appropriate credentials
2. **Terraform** >= 1.0 installed
3. **Docker** for building container images
4. **AWS profile** configured (default: `dhanu_aws`)
5. **Bedrock model access** enabled in AWS Console

## Bedrock Model Setup

**IMPORTANT:** Before deploying, enable Bedrock model access:

1. Go to [AWS Bedrock Console](https://us-east-1.console.aws.amazon.com/bedrock/home?region=us-east-1#/modelaccess)
2. Click "Request model access"
3. Enable these models:
   - **Claude Instant** (`anthropic.claude-instant-v1`) - Primary Q&A model
   - **Claude 3 Haiku** (`anthropic.claude-3-haiku-20240307-v1:0`) - Backup model
   - **Titan Text Express** (`amazon.titan-text-express-v1`) - Currently working model
   - **Titan Embeddings v2** (`amazon.titan-embed-text-v2:0`) - For future features

## Quick Start

1. **Initialize Terraform:**
   ```bash
   ./deploy.sh init
   ```

2. **Review the plan:**
   ```bash
   ./deploy.sh plan
   ```

3. **Deploy infrastructure:**
   ```bash
   ./deploy.sh apply
   ```

4. **Build and push container:**
   ```bash
   # Get ECR login
   aws ecr get-login-password --region us-east-1 --profile dhanu_aws | docker login --username AWS --password-stdin $(terraform output -raw ecr_repository_url | cut -d'/' -f1)
   
   # Build and push from backend directory
   cd ../backend
   docker build -t ncdhhs-pdf-qa-backend .
   docker tag ncdhhs-pdf-qa-backend:latest $(cd ../aws && terraform output -raw ecr_repository_url):latest
   docker push $(cd ../aws && terraform output -raw ecr_repository_url):latest
   ```

5. **Update ECS service:**
   ```bash
   aws ecs update-service --cluster $(terraform output -raw ecs_cluster_name) --service ncdhhs-pdf-qa-dev-service --force-new-deployment --profile dhanu_aws --region us-east-1
   ```

6. **Access the application:**
   ```bash
   echo "Application URL: $(terraform output -raw application_url)"
   ```

## Configuration

Edit `terraform.tfvars` to customize:

```hcl
project_name = "ncdhhs-pdf-qa"
environment  = "dev"
aws_region   = "us-east-1"
aws_profile  = "dhanu_aws"

container_cpu    = 1024  # CPU units (1024 = 1 vCPU)
container_memory = 2048  # Memory in MB
desired_count    = 1     # Number of ECS tasks

redis_node_type = "cache.t3.micro"  # Redis instance type

# PDF Processing Configuration
alb_idle_timeout      = 300  # ALB timeout (5 minutes for large PDFs)
pdf_download_timeout  = 180  # PDF download timeout (3 minutes)

# Bedrock Models
enable_bedrock_models = [
  "anthropic.claude-instant-v1",
  "anthropic.claude-3-haiku-20240307-v1:0",
  "amazon.titan-text-express-v1",
  "amazon.titan-embed-text-v2:0"
]
```

## API Endpoints

Once deployed, the application provides:

- `GET /` - Welcome page
- `GET /health` - Health check
- `GET /docs` - API documentation
- `POST /process-pdf-batch` - Process PDFs from URLs
- `POST /ask-question` - AI-powered Q&A about processed documents
- `GET /documents` - List processed documents

## Testing the Application

1. **Process a PDF:**
   ```bash
   curl -X POST "$(terraform output -raw application_url)/process-pdf-batch" \
     -H "Content-Type: application/json" \
     -d '{
       "pdf_links": [
         {
           "title": "Test Document",
           "url": "https://www.orimi.com/pdf-test.pdf"
         }
       ]
     }'
   ```

2. **Ask questions:**
   ```bash
   curl -X POST "$(terraform output -raw application_url)/ask-question" \
     -H "Content-Type: application/json" \
     -d '{
       "question": "What is this document about?"
     }'
   ```

## Commands

- `./deploy.sh init` - Initialize Terraform
- `./deploy.sh plan` - Show deployment plan
- `./deploy.sh apply` - Deploy infrastructure
- `./deploy.sh destroy` - Destroy infrastructure
- `./deploy.sh output` - Show outputs

## Outputs

After deployment, you'll get:

- **application_url** - URL to access the application
- **ecr_repository_url** - ECR repository for container images
- **s3_bucket_name** - S3 bucket for documents
- **redis_endpoint** - Redis cluster endpoint
- **ecs_cluster_name** - ECS cluster name
- **bedrock_enabled_models** - List of configured Bedrock models
- **pdf_processing_config** - PDF processing configuration
- **bedrock_configuration** - Bedrock setup information

## Security

- All resources are tagged for cost tracking
- S3 bucket has encryption and public access blocked
- Security groups follow least-privilege principle
- IAM roles have minimal required permissions for Bedrock and S3
- Redis encryption at rest enabled
- Container runs with non-root user
- AWS profile isolation in containers

## Performance Optimizations

- **ALB timeout**: Extended to 300 seconds for large PDF processing
- **PDF download timeout**: 180 seconds for slow external servers
- **Container health checks**: Proper health monitoring
- **Bedrock model fallbacks**: Multiple AI models for reliability
- **S3 storage**: Efficient document storage and retrieval

## Cost Optimization

- Uses Fargate for serverless container execution
- Single Redis node for development
- ECR lifecycle policies to manage image storage
- CloudWatch log retention set to 7 days
- Bedrock pay-per-use pricing

## Monitoring

- **CloudWatch Logs**: `/ecs/ncdhhs-pdf-qa-dev-backend`
- **Bedrock Dashboard**: Monitor AI model usage and costs
- **ECS Service Metrics**: Container health and performance
- **ALB Metrics**: Request patterns and response times

## Troubleshooting

1. **ECS tasks not starting:**
   - Check CloudWatch logs: `/ecs/ncdhhs-pdf-qa-dev-backend`
   - Verify container image exists in ECR
   - Check security group rules
   - Verify IAM role permissions

2. **Bedrock access denied:**
   - Ensure models are enabled in Bedrock Console
   - Check IAM role has Bedrock permissions
   - Verify model ARNs in IAM policy

3. **PDF processing timeouts:**
   - Check ALB timeout settings (should be 300s)
   - Verify PDF download timeout (should be 180s)
   - Monitor CloudWatch logs for specific errors

4. **Load balancer health checks failing:**
   - Ensure `/health` endpoint is working
   - Check container port configuration
   - Verify security group allows ALB → ECS traffic

5. **Redis connection issues:**
   - Check security group allows ECS → Redis traffic
   - Verify Redis endpoint in ECS environment variables

## Cleanup

To destroy all resources:

```bash
./deploy.sh destroy
```

**Warning:** This will permanently delete all data in S3 and Redis!

## Production Considerations

For production deployment:

1. **Enable HTTPS** with ACM certificate
2. **Use private subnets** for ECS tasks
3. **Enable Redis Multi-AZ** for high availability
4. **Increase desired_count** for load distribution
5. **Set up CloudWatch alarms** for monitoring
6. **Enable AWS Config** for compliance
7. **Use Secrets Manager** for sensitive configuration
