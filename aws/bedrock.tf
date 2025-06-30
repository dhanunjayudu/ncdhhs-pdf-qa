# Bedrock Model Access Configuration
# Note: Model access must be manually enabled in AWS Console
# This file documents the models used by the application

locals {
  bedrock_models = {
    # Primary AI model for Q&A
    claude_instant = {
      id          = "anthropic.claude-instant-v1"
      name        = "Claude Instant"
      description = "Fast, cost-effective model for Q&A"
      status      = "LEGACY"
    }
    
    # Backup AI model for Q&A
    claude_haiku = {
      id          = "anthropic.claude-3-haiku-20240307-v1:0"
      name        = "Claude 3 Haiku"
      description = "Higher quality responses, good balance of speed and accuracy"
      status      = "ACTIVE"
    }
    
    # Currently working AI model
    titan_text = {
      id          = "amazon.titan-text-express-v1"
      name        = "Titan Text Express"
      description = "Amazon's text generation model - currently enabled and working"
      status      = "ACTIVE"
    }
    
    # Text embedding model (for future use)
    titan_embed = {
      id          = "amazon.titan-embed-text-v2:0"
      name        = "Titan Text Embeddings v2"
      description = "Text embeddings for semantic search"
      status      = "ACTIVE"
    }
  }
}

# Data source to check available models
data "aws_bedrock_foundation_models" "available" {
  by_output_modality = "TEXT"
}

# Output information about Bedrock configuration
output "bedrock_configuration" {
  description = "Bedrock model configuration and status"
  value = {
    models_configured = local.bedrock_models
    region           = var.aws_region
    access_note      = "Model access must be manually enabled in AWS Bedrock Console"
    console_url      = "https://${var.aws_region}.console.aws.amazon.com/bedrock/home?region=${var.aws_region}#/modelaccess"
  }
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
            ["AWS/Bedrock", "Invocations", "ModelId", "anthropic.claude-instant-v1"],
            [".", ".", ".", "anthropic.claude-3-haiku-20240307-v1:0"],
            [".", ".", ".", "amazon.titan-text-express-v1"]
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
            ["AWS/Bedrock", "InputTokenCount", "ModelId", "anthropic.claude-instant-v1"],
            [".", "OutputTokenCount", ".", "."],
            [".", "InputTokenCount", ".", "anthropic.claude-3-haiku-20240307-v1:0"],
            [".", "OutputTokenCount", ".", "."],
            [".", "InputTokenCount", ".", "amazon.titan-text-express-v1"],
            [".", "OutputTokenCount", ".", "."]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Bedrock Token Usage"
          period  = 300
        }
      }
    ]
  })
}
