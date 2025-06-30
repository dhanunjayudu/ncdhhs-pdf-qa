# Enhanced Bedrock Configuration with Knowledge Base and Guardrails
# This file creates the complete Bedrock infrastructure for NCDHHS PDF Q&A

locals {
  bedrock_models = {
    # Primary AI model for Q&A
    claude_sonnet = {
      id          = "anthropic.claude-3-sonnet-20240229-v1:0"
      name        = "Claude 3 Sonnet"
      description = "High-quality model for complex Q&A with guardrails support"
      status      = "ACTIVE"
    }
    
    # Backup AI model for Q&A
    claude_haiku = {
      id          = "anthropic.claude-3-haiku-20240307-v1:0"
      name        = "Claude 3 Haiku"
      description = "Fast model for simple Q&A tasks"
      status      = "ACTIVE"
    }
    
    # Text embedding model for knowledge base
    titan_embed = {
      id          = "amazon.titan-embed-text-v1"
      name        = "Titan Text Embeddings v1"
      description = "Text embeddings for semantic search in knowledge base"
      status      = "ACTIVE"
    }
  }
}

# Random suffix for unique resource names
resource "random_id" "bedrock_suffix" {
  byte_length = 4
}

# S3 bucket for Bedrock Knowledge Base documents
resource "aws_s3_bucket" "bedrock_knowledge_base" {
  bucket = "${local.name_prefix}-bedrock-kb-${random_id.bedrock_suffix.hex}"
  
  tags = merge(local.common_tags, {
    Name = "Bedrock Knowledge Base Bucket"
    Purpose = "Document storage for Bedrock Knowledge Base"
  })
}

resource "aws_s3_bucket_versioning" "bedrock_knowledge_base" {
  bucket = aws_s3_bucket.bedrock_knowledge_base.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "bedrock_knowledge_base" {
  bucket = aws_s3_bucket.bedrock_knowledge_base.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "bedrock_knowledge_base" {
  bucket = aws_s3_bucket.bedrock_knowledge_base.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# IAM role for Bedrock Knowledge Base
resource "aws_iam_role" "bedrock_knowledge_base" {
  name = "${local.name_prefix}-bedrock-kb-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "bedrock.amazonaws.com"
        }
      }
    ]
  })

  tags = merge(local.common_tags, {
    Name = "Bedrock Knowledge Base Role"
  })
}

# IAM policy for Bedrock Knowledge Base S3 access
resource "aws_iam_role_policy" "bedrock_knowledge_base_s3" {
  name = "${local.name_prefix}-bedrock-kb-s3-policy"
  role = aws_iam_role.bedrock_knowledge_base.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.bedrock_knowledge_base.arn,
          "${aws_s3_bucket.bedrock_knowledge_base.arn}/*"
        ]
      }
    ]
  })
}

# IAM policy for Bedrock Knowledge Base OpenSearch access
resource "aws_iam_role_policy" "bedrock_knowledge_base_opensearch" {
  name = "${local.name_prefix}-bedrock-kb-opensearch-policy"
  role = aws_iam_role.bedrock_knowledge_base.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "aoss:APIAccessAll"
        ]
        Resource = aws_opensearchserverless_collection.bedrock_knowledge_base.arn
      }
    ]
  })
}

# IAM policy for Bedrock model access
resource "aws_iam_role_policy" "bedrock_knowledge_base_models" {
  name = "${local.name_prefix}-bedrock-kb-models-policy"
  role = aws_iam_role.bedrock_knowledge_base.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel"
        ]
        Resource = [
          "arn:aws:bedrock:${var.aws_region}::foundation-model/amazon.titan-embed-text-v1"
        ]
      }
    ]
  })
}

# OpenSearch Serverless collection for Knowledge Base
resource "aws_opensearchserverless_collection" "bedrock_knowledge_base" {
  name        = "${local.name_prefix}-kb-collection"
  type        = "VECTORSEARCH"
  description = "OpenSearch collection for NCDHHS Bedrock Knowledge Base"

  tags = merge(local.common_tags, {
    Name = "Bedrock Knowledge Base Collection"
  })
}

# OpenSearch Serverless security policy
resource "aws_opensearchserverless_security_policy" "bedrock_knowledge_base_encryption" {
  name = "${local.name_prefix}-kb-encryption-policy"
  type = "encryption"
  
  policy = jsonencode({
    Rules = [
      {
        Resource = [
          "collection/${aws_opensearchserverless_collection.bedrock_knowledge_base.name}"
        ]
        ResourceType = "collection"
      }
    ]
    AWSOwnedKey = true
  })
}

resource "aws_opensearchserverless_security_policy" "bedrock_knowledge_base_network" {
  name = "${local.name_prefix}-kb-network-policy"
  type = "network"
  
  policy = jsonencode([
    {
      Rules = [
        {
          Resource = [
            "collection/${aws_opensearchserverless_collection.bedrock_knowledge_base.name}"
          ]
          ResourceType = "collection"
        }
      ]
      AllowFromPublic = true
    }
  ])
}

# Data access policy for OpenSearch Serverless
resource "aws_opensearchserverless_access_policy" "bedrock_knowledge_base" {
  name = "${local.name_prefix}-kb-access-policy"
  type = "data"
  
  policy = jsonencode([
    {
      Rules = [
        {
          Resource = [
            "collection/${aws_opensearchserverless_collection.bedrock_knowledge_base.name}"
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
            "index/${aws_opensearchserverless_collection.bedrock_knowledge_base.name}/*"
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
        aws_iam_role.bedrock_knowledge_base.arn
      ]
    }
  ])
}

# Bedrock Guardrail for content filtering
resource "aws_bedrock_guardrail" "ncdhhs_content_filter" {
  name                      = "${local.name_prefix}-content-guardrail"
  description              = "Content guardrail for NCDHHS PDF Q&A system"
  blocked_input_messaging  = "I cannot provide information on that topic. Please ask questions related to NCDHHS documents and services."
  blocked_outputs_messaging = "I cannot provide that type of information. Please ask questions about NCDHHS documents and services."

  # Topic-based filtering
  topic_policy_config {
    topics_config {
      name       = "Medical Information"
      definition = "Discussions about medical procedures, diagnoses, or treatments"
      examples   = [
        "What medication should I take?",
        "How do I treat this condition?",
        "What are the symptoms of..."
      ]
      type = "DENY"
    }

    topics_config {
      name       = "Personal Health Information"
      definition = "Requests for personal medical advice or diagnosis"
      examples   = [
        "What is wrong with me?",
        "Should I see a doctor?",
        "Am I sick?"
      ]
      type = "DENY"
    }
  }

  # Content filtering
  content_policy_config {
    filters_config {
      input_strength  = "HIGH"
      output_strength = "HIGH"
      type           = "SEXUAL"
    }

    filters_config {
      input_strength  = "HIGH"
      output_strength = "HIGH"
      type           = "VIOLENCE"
    }

    filters_config {
      input_strength  = "HIGH"
      output_strength = "HIGH"
      type           = "HATE"
    }

    filters_config {
      input_strength  = "MEDIUM"
      output_strength = "MEDIUM"
      type           = "INSULTS"
    }

    filters_config {
      input_strength  = "HIGH"
      output_strength = "HIGH"
      type           = "MISCONDUCT"
    }
  }

  # Word filtering
  word_policy_config {
    words_config {
      text = "confidential"
    }

    words_config {
      text = "classified"
    }

    words_config {
      text = "internal use only"
    }

    managed_word_lists_config {
      type = "PROFANITY"
    }
  }

  # PII filtering
  sensitive_information_policy_config {
    pii_entities_config {
      action = "BLOCK"
      type   = "EMAIL"
    }

    pii_entities_config {
      action = "BLOCK"
      type   = "PHONE"
    }

    pii_entities_config {
      action = "BLOCK"
      type   = "SSN"
    }

    pii_entities_config {
      action = "BLOCK"
      type   = "CREDIT_DEBIT_CARD_NUMBER"
    }

    regexes_config {
      action      = "BLOCK"
      description = "Block patient ID patterns"
      name        = "Patient ID Pattern"
      pattern     = "P\\d{6,8}"
    }
  }

  tags = merge(local.common_tags, {
    Name = "NCDHHS Content Guardrail"
  })
}

# Bedrock Knowledge Base
resource "aws_bedrock_knowledge_base" "ncdhhs_pdf_kb" {
  name     = "${local.name_prefix}-knowledge-base"
  role_arn = aws_iam_role.bedrock_knowledge_base.arn
  
  description = "Knowledge base for NCDHHS PDF documents and Q&A system"

  knowledge_base_configuration {
    type = "VECTOR"
    vector_knowledge_base_configuration {
      embedding_model_arn = "arn:aws:bedrock:${var.aws_region}::foundation-model/amazon.titan-embed-text-v1"
      embedding_model_configuration {
        bedrock_embedding_model_configuration {
          dimensions = 1536
        }
      }
    }
  }

  storage_configuration {
    type = "OPENSEARCH_SERVERLESS"
    opensearch_serverless_configuration {
      collection_arn    = aws_opensearchserverless_collection.bedrock_knowledge_base.arn
      vector_index_name = "ncdhhs-vector-index"
      field_mapping {
        vector_field   = "bedrock-knowledge-base-default-vector"
        text_field     = "AMAZON_BEDROCK_TEXT_CHUNK"
        metadata_field = "AMAZON_BEDROCK_METADATA"
      }
    }
  }

  tags = merge(local.common_tags, {
    Name = "NCDHHS PDF Knowledge Base"
  })

  depends_on = [
    aws_opensearchserverless_collection.bedrock_knowledge_base,
    aws_opensearchserverless_access_policy.bedrock_knowledge_base,
    aws_iam_role_policy.bedrock_knowledge_base_s3,
    aws_iam_role_policy.bedrock_knowledge_base_opensearch,
    aws_iam_role_policy.bedrock_knowledge_base_models
  ]
}

# Data source for the Knowledge Base
resource "aws_bedrock_data_source" "ncdhhs_pdf_documents" {
  knowledge_base_id = aws_bedrock_knowledge_base.ncdhhs_pdf_kb.id
  name             = "${local.name_prefix}-pdf-data-source"
  description      = "Data source for NCDHHS PDF documents"

  data_source_configuration {
    type = "S3"
    s3_configuration {
      bucket_arn = aws_s3_bucket.bedrock_knowledge_base.arn
      inclusion_prefixes = ["documents/"]
    }
  }

  vector_ingestion_configuration {
    chunking_configuration {
      chunking_strategy = "FIXED_SIZE"
      fixed_size_chunking_configuration {
        max_tokens         = 512
        overlap_percentage = 20
      }
    }
  }
}

# Data source to check available models
data "aws_bedrock_foundation_models" "available" {
  by_output_modality = "TEXT"
}

# CloudWatch dashboard for monitoring Bedrock usage
resource "aws_cloudwatch_dashboard" "bedrock_monitoring" {
  dashboard_name = "${local.name_prefix}-bedrock-monitoring"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/Bedrock", "Invocations", "ModelId", "anthropic.claude-3-sonnet-20240229-v1:0"],
            [".", ".", ".", "anthropic.claude-3-haiku-20240307-v1:0"],
            [".", ".", ".", "amazon.titan-embed-text-v1"]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Bedrock Model Invocations"
          period  = 300
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/Bedrock", "InputTokenCount", "ModelId", "anthropic.claude-3-sonnet-20240229-v1:0"],
            [".", "OutputTokenCount", ".", "."],
            [".", "InputTokenCount", ".", "anthropic.claude-3-haiku-20240307-v1:0"],
            [".", "OutputTokenCount", ".", "."],
            [".", "InputTokenCount", ".", "amazon.titan-embed-text-v1"],
            [".", "OutputTokenCount", ".", "."]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Bedrock Token Usage"
          period  = 300
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 12
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/BedrockAgent", "KnowledgeBaseQuery", "KnowledgeBaseId", aws_bedrock_knowledge_base.ncdhhs_pdf_kb.id]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Knowledge Base Queries"
          period  = 300
        }
      }
    ]
  })

  tags = merge(local.common_tags, {
    Name = "Bedrock Monitoring Dashboard"
  })
}
