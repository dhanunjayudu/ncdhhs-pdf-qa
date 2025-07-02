# OpenSearch Serverless Collection for Bedrock Knowledge Base
resource "aws_opensearchserverless_security_policy" "bedrock_encryption" {
  name = "bedrock-kb-encryption"
  type = "encryption"
  
  policy = jsonencode({
    Rules = [
      {
        Resource = [
          "collection/bedrock-kb"
        ]
        ResourceType = "collection"
      }
    ]
    AWSOwnedKey = true
  })
}

resource "aws_opensearchserverless_security_policy" "bedrock_network" {
  name = "bedrock-kb-network"
  type = "network"
  
  policy = jsonencode([
    {
      Rules = [
        {
          Resource = [
            "collection/bedrock-kb"
          ]
          ResourceType = "collection"
        },
        {
          Resource = [
            "collection/bedrock-kb"
          ]
          ResourceType = "dashboard"
        }
      ]
      AllowFromPublic = true
    }
  ])
}

resource "aws_opensearchserverless_access_policy" "bedrock_access" {
  name = "bedrock-kb-access"
  type = "data"
  
  policy = jsonencode([
    {
      Rules = [
        {
          Resource = [
            "collection/bedrock-kb"
          ]
          Permission = [
            "aoss:CreateCollectionItems",
            "aoss:DeleteCollectionItems", 
            "aoss:UpdateCollectionItems",
            "aoss:DescribeCollectionItems"
          ]
          ResourceType = "collection"
        },
        {
          Resource = [
            "index/bedrock-kb/*"
          ]
          Permission = [
            "aoss:CreateIndex",
            "aoss:DeleteIndex",
            "aoss:UpdateIndex",
            "aoss:DescribeIndex",
            "aoss:ReadDocument",
            "aoss:WriteDocument"
          ]
          ResourceType = "index"
        }
      ]
      Principal = [
        data.aws_caller_identity.current.arn,
        aws_iam_role.bedrock_knowledge_base.arn,
        "arn:aws:iam::${data.aws_caller_identity.current.account_id}:user/dhanu_bedrock"
      ]
    }
  ])
}

resource "aws_opensearchserverless_collection" "bedrock_knowledge_base" {
  name = "bedrock-kb"
  type = "VECTORSEARCH"
  
  depends_on = [
    aws_opensearchserverless_security_policy.bedrock_encryption,
    aws_opensearchserverless_security_policy.bedrock_network,
    aws_opensearchserverless_access_policy.bedrock_access
  ]

  tags = {
    Name        = "Bedrock Knowledge Base Collection"
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "Terraform"
    Purpose     = "Vector storage for Bedrock Knowledge Base"
  }
}

# Output the collection details
output "opensearch_serverless_collection_id" {
  description = "ID of the OpenSearch Serverless collection"
  value       = aws_opensearchserverless_collection.bedrock_knowledge_base.id
}

output "opensearch_serverless_collection_endpoint" {
  description = "Endpoint of the OpenSearch Serverless collection"
  value       = aws_opensearchserverless_collection.bedrock_knowledge_base.collection_endpoint
}

output "opensearch_serverless_collection_arn" {
  description = "ARN of the OpenSearch Serverless collection"
  value       = aws_opensearchserverless_collection.bedrock_knowledge_base.arn
}
