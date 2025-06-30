#!/bin/bash

# Setup AWS Bedrock Knowledge Base and Guardrails for NCDHHS PDF Q&A
# This script creates the necessary AWS resources for enhanced AI capabilities

set -e

echo "🚀 Setting up AWS Bedrock infrastructure for NCDHHS PDF Q&A..."

# Configuration
REGION="us-east-1"
KB_NAME="ncdhhs-pdf-knowledge-base"
GUARDRAIL_NAME="ncdhhs-content-guardrail"
S3_BUCKET="ncdhhs-bedrock-knowledge-base-$(date +%s)"
ROLE_NAME="BedrockKnowledgeBaseRole-NCDHHS"
COLLECTION_NAME="ncdhhs-knowledge-base"

echo "📋 Configuration:"
echo "  Region: $REGION"
echo "  Knowledge Base: $KB_NAME"
echo "  Guardrail: $GUARDRAIL_NAME"
echo "  S3 Bucket: $S3_BUCKET"
echo ""

# 1. Create S3 bucket for knowledge base
echo "📦 Creating S3 bucket for knowledge base..."
aws s3 mb s3://$S3_BUCKET --region $REGION

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket $S3_BUCKET \
  --versioning-configuration Status=Enabled

echo "✅ S3 bucket created: $S3_BUCKET"

# 2. Create IAM role for Bedrock Knowledge Base
echo "🔐 Creating IAM role for Bedrock Knowledge Base..."

# Trust policy for Bedrock
cat > bedrock-trust-policy.json << EOF
{
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
EOF

# Create the role
aws iam create-role \
  --role-name $ROLE_NAME \
  --assume-role-policy-document file://bedrock-trust-policy.json \
  --description "Role for Bedrock Knowledge Base access" || echo "Role may already exist"

# Attach policies
aws iam attach-role-policy \
  --role-name $ROLE_NAME \
  --policy-arn arn:aws:iam::aws:policy/AmazonBedrockFullAccess

# Create custom policy for S3 access
cat > bedrock-s3-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::$S3_BUCKET",
        "arn:aws:s3:::$S3_BUCKET/*"
      ]
    }
  ]
}
EOF

aws iam put-role-policy \
  --role-name $ROLE_NAME \
  --policy-name BedrockS3Access \
  --policy-document file://bedrock-s3-policy.json

# Get role ARN
ROLE_ARN=$(aws iam get-role --role-name $ROLE_NAME --query 'Role.Arn' --output text)
echo "✅ IAM role created: $ROLE_ARN"

# 3. Create OpenSearch Serverless collection
echo "🔍 Creating OpenSearch Serverless collection..."

# Create collection
aws opensearchserverless create-collection \
  --name $COLLECTION_NAME \
  --description "OpenSearch collection for NCDHHS Bedrock Knowledge Base" \
  --type VECTORSEARCH || echo "Collection may already exist"

# Wait for collection to be active
echo "⏳ Waiting for OpenSearch collection to be active..."
while true; do
  STATUS=$(aws opensearchserverless list-collections --collection-filters name=$COLLECTION_NAME --query 'collectionSummaries[0].status' --output text)
  if [ "$STATUS" = "ACTIVE" ]; then
    break
  fi
  echo "  Collection status: $STATUS"
  sleep 30
done

COLLECTION_ARN=$(aws opensearchserverless list-collections --collection-filters name=$COLLECTION_NAME --query 'collectionSummaries[0].arn' --output text)
echo "✅ OpenSearch collection created: $COLLECTION_ARN"

# 4. Create Bedrock Guardrail
echo "🛡️ Creating Bedrock Guardrail..."

cat > guardrail-config.json << EOF
{
  "name": "$GUARDRAIL_NAME",
  "description": "Content guardrail for NCDHHS PDF Q&A system",
  "topicPolicyConfig": {
    "topicsConfig": [
      {
        "name": "Medical Information",
        "definition": "Discussions about medical procedures, diagnoses, or treatments",
        "examples": [
          "What medication should I take?",
          "How do I treat this condition?",
          "What are the symptoms of..."
        ],
        "type": "DENY"
      },
      {
        "name": "Personal Health Information",
        "definition": "Requests for personal medical advice or diagnosis",
        "examples": [
          "What is wrong with me?",
          "Should I see a doctor?",
          "Am I sick?"
        ],
        "type": "DENY"
      }
    ]
  },
  "contentPolicyConfig": {
    "filtersConfig": [
      {
        "type": "SEXUAL",
        "inputStrength": "HIGH",
        "outputStrength": "HIGH"
      },
      {
        "type": "VIOLENCE",
        "inputStrength": "HIGH",
        "outputStrength": "HIGH"
      },
      {
        "type": "HATE",
        "inputStrength": "HIGH",
        "outputStrength": "HIGH"
      },
      {
        "type": "INSULTS",
        "inputStrength": "MEDIUM",
        "outputStrength": "MEDIUM"
      },
      {
        "type": "MISCONDUCT",
        "inputStrength": "HIGH",
        "outputStrength": "HIGH"
      }
    ]
  },
  "wordPolicyConfig": {
    "wordsConfig": [
      {
        "text": "confidential"
      },
      {
        "text": "classified"
      },
      {
        "text": "internal use only"
      }
    ],
    "managedWordListsConfig": [
      {
        "type": "PROFANITY"
      }
    ]
  },
  "sensitiveInformationPolicyConfig": {
    "piiEntitiesConfig": [
      {
        "type": "EMAIL",
        "action": "BLOCK"
      },
      {
        "type": "PHONE",
        "action": "BLOCK"
      },
      {
        "type": "SSN",
        "action": "BLOCK"
      },
      {
        "type": "CREDIT_DEBIT_CARD_NUMBER",
        "action": "BLOCK"
      }
    ],
    "regexesConfig": [
      {
        "name": "Patient ID Pattern",
        "description": "Block patient ID patterns",
        "pattern": "P\\\\d{6,8}",
        "action": "BLOCK"
      }
    ]
  },
  "blockedInputMessaging": "I cannot provide information on that topic. Please ask questions related to NCDHHS documents and services.",
  "blockedOutputsMessaging": "I cannot provide that type of information. Please ask questions about NCDHHS documents and services."
}
EOF

GUARDRAIL_RESULT=$(aws bedrock create-guardrail --cli-input-json file://guardrail-config.json --region $REGION)
GUARDRAIL_ID=$(echo $GUARDRAIL_RESULT | jq -r '.guardrailId')
GUARDRAIL_VERSION=$(echo $GUARDRAIL_RESULT | jq -r '.version')

echo "✅ Guardrail created: $GUARDRAIL_ID (version $GUARDRAIL_VERSION)"

# 5. Create Bedrock Knowledge Base
echo "🧠 Creating Bedrock Knowledge Base..."

cat > knowledge-base-config.json << EOF
{
  "name": "$KB_NAME",
  "description": "Knowledge base for NCDHHS PDF documents and Q&A system",
  "roleArn": "$ROLE_ARN",
  "knowledgeBaseConfiguration": {
    "type": "VECTOR",
    "vectorKnowledgeBaseConfiguration": {
      "embeddingModelArn": "arn:aws:bedrock:$REGION::foundation-model/amazon.titan-embed-text-v1",
      "embeddingModelConfiguration": {
        "bedrockEmbeddingModelConfiguration": {
          "dimensions": 1536
        }
      }
    }
  },
  "storageConfiguration": {
    "type": "OPENSEARCH_SERVERLESS",
    "opensearchServerlessConfiguration": {
      "collectionArn": "$COLLECTION_ARN",
      "vectorIndexName": "ncdhhs-vector-index",
      "fieldMapping": {
        "vectorField": "bedrock-knowledge-base-default-vector",
        "textField": "AMAZON_BEDROCK_TEXT_CHUNK",
        "metadataField": "AMAZON_BEDROCK_METADATA"
      }
    }
  }
}
EOF

KB_RESULT=$(aws bedrock-agent create-knowledge-base --cli-input-json file://knowledge-base-config.json --region $REGION)
KB_ID=$(echo $KB_RESULT | jq -r '.knowledgeBase.knowledgeBaseId')

echo "✅ Knowledge Base created: $KB_ID"

# 6. Create Data Source
echo "📄 Creating Data Source for Knowledge Base..."

cat > data-source-config.json << EOF
{
  "knowledgeBaseId": "$KB_ID",
  "name": "ncdhhs-pdf-data-source",
  "description": "Data source for NCDHHS PDF documents",
  "dataSourceConfiguration": {
    "type": "S3",
    "s3Configuration": {
      "bucketArn": "arn:aws:s3:::$S3_BUCKET",
      "inclusionPrefixes": ["documents/"]
    }
  },
  "vectorIngestionConfiguration": {
    "chunkingConfiguration": {
      "chunkingStrategy": "FIXED_SIZE",
      "fixedSizeChunkingConfiguration": {
        "maxTokens": 512,
        "overlapPercentage": 20
      }
    }
  }
}
EOF

DS_RESULT=$(aws bedrock-agent create-data-source --cli-input-json file://data-source-config.json --region $REGION)
DS_ID=$(echo $DS_RESULT | jq -r '.dataSource.dataSourceId')

echo "✅ Data Source created: $DS_ID"

# 7. Create environment file with configuration
echo "📝 Creating environment configuration..."

cat > bedrock-config.env << EOF
# AWS Bedrock Configuration for NCDHHS PDF Q&A
AWS_REGION=$REGION
BEDROCK_KNOWLEDGE_BASE_ID=$KB_ID
BEDROCK_DATA_SOURCE_ID=$DS_ID
BEDROCK_GUARDRAIL_ID=$GUARDRAIL_ID
BEDROCK_GUARDRAIL_VERSION=$GUARDRAIL_VERSION
S3_KNOWLEDGE_BASE_BUCKET=$S3_BUCKET
OPENSEARCH_COLLECTION_ARN=$COLLECTION_ARN
IAM_ROLE_ARN=$ROLE_ARN
EOF

echo "✅ Configuration saved to bedrock-config.env"

# 8. Clean up temporary files
rm -f bedrock-trust-policy.json bedrock-s3-policy.json guardrail-config.json knowledge-base-config.json data-source-config.json

echo ""
echo "🎉 AWS Bedrock infrastructure setup complete!"
echo ""
echo "📋 Summary:"
echo "  ✅ S3 Bucket: $S3_BUCKET"
echo "  ✅ IAM Role: $ROLE_ARN"
echo "  ✅ OpenSearch Collection: $COLLECTION_ARN"
echo "  ✅ Guardrail: $GUARDRAIL_ID (v$GUARDRAIL_VERSION)"
echo "  ✅ Knowledge Base: $KB_ID"
echo "  ✅ Data Source: $DS_ID"
echo ""
echo "🔧 Next Steps:"
echo "  1. Add the configuration from bedrock-config.env to your backend environment"
echo "  2. Upload PDF documents to s3://$S3_BUCKET/documents/"
echo "  3. Sync the data source to index documents"
echo "  4. Test the enhanced Q&A functionality"
echo ""
echo "💡 To sync documents:"
echo "  aws bedrock-agent start-ingestion-job --knowledge-base-id $KB_ID --data-source-id $DS_ID --region $REGION"
