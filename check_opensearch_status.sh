#!/bin/bash

echo "🔍 Checking OpenSearch domain creation status..."

# Check OpenSearch domain status
DOMAIN_STATUS=$(aws opensearch describe-domain --domain-name ncdhhs-pdf-qa-opensearch --query 'DomainStatus.Processing' --output text 2>/dev/null)

if [ "$DOMAIN_STATUS" = "True" ]; then
    echo "⏳ OpenSearch domain is still being created..."
    echo "   This typically takes 10-15 minutes."
    echo "   You can check status with: aws opensearch describe-domain --domain-name ncdhhs-pdf-qa-opensearch"
elif [ "$DOMAIN_STATUS" = "False" ]; then
    echo "✅ OpenSearch domain is ready!"
    
    # Get the endpoint
    ENDPOINT=$(aws opensearch describe-domain --domain-name ncdhhs-pdf-qa-opensearch --query 'DomainStatus.Endpoint' --output text 2>/dev/null)
    echo "🔗 Endpoint: https://$ENDPOINT"
    
    # Check if Terraform apply is complete
    echo ""
    echo "🚀 Continuing with Terraform deployment..."
    cd /Users/dhanunjayudusurisetty/ncdhhs-pdf-qa/aws
    terraform apply -auto-approve
else
    echo "❓ OpenSearch domain not found or error occurred"
    echo "   Checking Terraform state..."
    cd /Users/dhanunjayudusurisetty/ncdhhs-pdf-qa/aws
    terraform show | grep opensearch || echo "No OpenSearch resources in state"
fi
