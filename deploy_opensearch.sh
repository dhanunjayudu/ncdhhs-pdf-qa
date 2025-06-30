#!/bin/bash

# Deploy NC DHHS PDF Q&A with OpenSearch Vector Database
set -e

echo "🚀 Deploying NC DHHS PDF Q&A with OpenSearch Vector Database..."

# Check if AWS CLI is configured
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo "❌ AWS CLI not configured. Please run 'aws configure' first."
    exit 1
fi

# Build and push Docker image
echo "📦 Building Docker image with OpenSearch support..."
cd backend

# Get AWS account ID and region
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=${AWS_REGION:-us-east-1}
ECR_REPOSITORY="ncdhhs-pdf-qa-backend"

# Login to ECR
echo "🔐 Logging in to ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Build image
echo "🏗️ Building Docker image..."
docker build -f Dockerfile_opensearch -t $ECR_REPOSITORY:latest .

# Tag and push image
echo "📤 Pushing image to ECR..."
docker tag $ECR_REPOSITORY:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:latest

cd ..

# Deploy infrastructure
echo "🏗️ Deploying infrastructure with Terraform..."
cd aws

# Initialize Terraform
terraform init

# Plan deployment
echo "📋 Planning Terraform deployment..."
terraform plan -var="aws_region=$AWS_REGION"

# Apply deployment
echo "🚀 Applying Terraform deployment..."
terraform apply -auto-approve -var="aws_region=$AWS_REGION"

# Get outputs
echo "📊 Getting deployment outputs..."
ALB_DNS=$(terraform output -raw alb_dns_name)
OPENSEARCH_ENDPOINT=$(terraform output -raw opensearch_endpoint)

echo ""
echo "✅ Deployment completed successfully!"
echo ""
echo "🌐 Application URL: http://$ALB_DNS"
echo "🔍 OpenSearch Endpoint: https://$OPENSEARCH_ENDPOINT"
echo ""
echo "📝 Key Features:"
echo "   • Vector database powered by Amazon OpenSearch"
echo "   • Semantic search with 1024-dimensional embeddings"
echo "   • Automatic document chunking and indexing"
echo "   • AWS Bedrock integration for AI responses"
echo "   • Scalable infrastructure on AWS ECS Fargate"
echo ""
echo "🔧 To test the system:"
echo "   1. Visit: http://$ALB_DNS/docs for API documentation"
echo "   2. Check health: curl http://$ALB_DNS/health"
echo "   3. Process documents via the /process-pdf-batch endpoint"
echo "   4. Ask questions via the /ask endpoint"
echo ""
echo "⚠️  Note: OpenSearch domain may take 10-15 minutes to be fully ready"

cd ..

echo "🎉 Deployment script completed!"
