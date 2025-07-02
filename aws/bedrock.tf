# Simplified S3 + Bedrock Configuration (Compatible with current AWS provider)
# This creates the essential infrastructure for the simplified architecture

locals {
  # Select models based on preference
  selected_models = var.bedrock_models_to_enable[var.bedrock_model_preference]
  
  # Extract individual model IDs for easier reference
  primary_model_id    = local.selected_models.primary_model_id
  fast_model_id      = local.selected_models.fast_model_id
  embedding_model_id = local.selected_models.embedding_model_id
  
  # Embedding model ARN for knowledge base
  embedding_model_arn = "arn:aws:bedrock:${var.aws_region}::foundation-model/${local.embedding_model_id}"
  
  bedrock_models = {
    # Primary AI model for Q&A
    primary = {
      id          = local.primary_model_id
      name        = "Primary Q&A Model"
      description = "High-quality model for complex Q&A tasks"
      status      = "ACTIVE"
    }
    
    # Fast AI model for Q&A
    fast = {
      id          = local.fast_model_id
      name        = "Fast Q&A Model"
      description = "Fast model for simple Q&A tasks"
      status      = "ACTIVE"
    }
    
    # Text embedding model for knowledge base
    embedding = {
      id          = local.embedding_model_id
      name        = "Text Embeddings"
      description = "Text embeddings for semantic search in knowledge base"
      status      = "ACTIVE"
    }
  }
}

# Random suffix for unique resource names
resource "random_id" "bedrock_suffix" {
  byte_length = 4
}

# S3 bucket for Bedrock Knowledge Base documents (main storage)
resource "aws_s3_bucket" "bedrock_knowledge_base" {
  bucket = "${local.name_prefix}-bedrock-kb-${random_id.bedrock_suffix.hex}"
  
  tags = merge(local.common_tags, {
    Name = "Bedrock Knowledge Base Bucket"
    Purpose = "Primary storage for PDF documents"
    Architecture = "Simplified S3 + Bedrock"
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

# IAM role for Bedrock Knowledge Base (for manual setup)
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
          "s3:ListBucket",
          "s3:GetBucketLocation"
        ]
        Resource = [
          aws_s3_bucket.bedrock_knowledge_base.arn,
          "${aws_s3_bucket.bedrock_knowledge_base.arn}/*"
        ]
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
          local.embedding_model_arn
        ]
      }
    ]
  })
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
      type   = "US_SOCIAL_SECURITY_NUMBER"
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
            ["AWS/Bedrock", "Invocations", "ModelId", local.primary_model_id],
            [".", ".", ".", local.fast_model_id],
            [".", ".", ".", local.embedding_model_id]
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
            ["AWS/Bedrock", "InputTokenCount", "ModelId", local.primary_model_id],
            [".", "OutputTokenCount", ".", "."],
            [".", "InputTokenCount", ".", local.fast_model_id],
            [".", "OutputTokenCount", ".", "."],
            [".", "InputTokenCount", ".", local.embedding_model_id],
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
            ["AWS/S3", "NumberOfObjects", "BucketName", aws_s3_bucket.bedrock_knowledge_base.bucket, "StorageType", "AllStorageTypes"]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "S3 Knowledge Base Documents"
          period  = 300
        }
      }
    ]
  })
}
