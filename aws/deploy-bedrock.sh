#!/bin/bash

# Deploy Enhanced NCDHHS PDF Q&A with Bedrock Infrastructure
# This script applies Terraform changes to create Bedrock Knowledge Base and Guardrails

set -e

echo "🚀 Deploying Enhanced NCDHHS PDF Q&A with AWS Bedrock..."
echo "=================================================="

# Check if we're in the right directory
if [ ! -f "main.tf" ]; then
    echo "❌ Error: main.tf not found. Please run this script from the aws/ directory."
    exit 1
fi

# Check if Terraform is installed
if ! command -v terraform &> /dev/null; then
    echo "❌ Error: Terraform is not installed. Please install Terraform first."
    exit 1
fi

# Check if AWS CLI is configured
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ Error: AWS CLI is not configured. Please configure AWS credentials first."
    exit 1
fi

echo "✅ Prerequisites check passed"
echo ""

# Initialize Terraform if needed
if [ ! -d ".terraform" ]; then
    echo "🔧 Initializing Terraform..."
    terraform init
    echo ""
fi

# Validate Terraform configuration
echo "🔍 Validating Terraform configuration..."
terraform validate
if [ $? -ne 0 ]; then
    echo "❌ Terraform validation failed. Please fix the configuration errors."
    exit 1
fi
echo "✅ Terraform configuration is valid"
echo ""

# Plan the deployment
echo "📋 Planning Terraform deployment..."
terraform plan -out=tfplan
if [ $? -ne 0 ]; then
    echo "❌ Terraform plan failed. Please check the configuration."
    exit 1
fi
echo ""

# Ask for confirmation
echo "🤔 Review the plan above. Do you want to apply these changes? (y/N)"
read -r response
if [[ ! "$response" =~ ^[Yy]$ ]]; then
    echo "❌ Deployment cancelled by user."
    rm -f tfplan
    exit 0
fi

# Apply the changes
echo "🚀 Applying Terraform changes..."
terraform apply tfplan
if [ $? -ne 0 ]; then
    echo "❌ Terraform apply failed."
    rm -f tfplan
    exit 1
fi

# Clean up plan file
rm -f tfplan

echo ""
echo "🎉 Deployment completed successfully!"
echo "=================================="

# Get outputs
echo "📋 Deployment Summary:"
echo ""

# Basic infrastructure
echo "🏗️  Infrastructure:"
echo "   Application URL: $(terraform output -raw application_url)"
echo "   ECS Cluster: $(terraform output -raw ecs_cluster_name)"
echo "   OpenSearch Endpoint: $(terraform output -raw opensearch_endpoint)"
echo ""

# Bedrock configuration
echo "🧠 Bedrock Configuration:"
echo "   Knowledge Base ID: $(terraform output -raw bedrock_knowledge_base_id)"
echo "   Data Source ID: $(terraform output -raw bedrock_data_source_id)"
echo "   Guardrail ID: $(terraform output -raw bedrock_guardrail_id)"
echo "   Guardrail Version: $(terraform output -raw bedrock_guardrail_version)"
echo "   S3 Knowledge Base Bucket: $(terraform output -raw bedrock_s3_bucket)"
echo ""

# Environment variables for backend
echo "🔧 Environment Variables (for backend configuration):"
terraform output bedrock_environment_variables
echo ""

# Next steps
echo "📝 Next Steps:"
echo "1. 🔐 Enable Bedrock model access in AWS Console:"
echo "   https://$(terraform output -raw aws_region).console.aws.amazon.com/bedrock/home?region=$(terraform output -raw aws_region)#/modelaccess"
echo ""
echo "2. 📄 Upload documents to S3 bucket:"
echo "   aws s3 cp your-documents/ s3://$(terraform output -raw bedrock_s3_bucket)/documents/ --recursive"
echo ""
echo "3. 🔄 Sync the knowledge base:"
echo "   aws bedrock-agent start-ingestion-job \\"
echo "     --knowledge-base-id $(terraform output -raw bedrock_knowledge_base_id) \\"
echo "     --data-source-id $(terraform output -raw bedrock_data_source_id) \\"
echo "     --region $(terraform output -raw aws_region)"
echo ""
echo "4. 🐳 Update and deploy your backend container with new environment variables"
echo ""
echo "5. 🧪 Test the enhanced Q&A functionality"
echo ""

# Save configuration to file
echo "💾 Saving configuration to bedrock-config.json..."
terraform output -json bedrock_configuration > bedrock-config.json
echo "✅ Configuration saved to bedrock-config.json"
echo ""

echo "🎊 Enhanced NCDHHS PDF Q&A with Bedrock is ready!"
echo "Visit your application at: $(terraform output -raw application_url)"
