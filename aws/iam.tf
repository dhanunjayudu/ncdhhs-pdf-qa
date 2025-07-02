# ECS Task Execution Role
resource "aws_iam_role" "ecs_task_execution" {
  name = "${local.name_prefix}-ECSTaskExecutionRole"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# ECS Task Role (for application permissions)
resource "aws_iam_role" "ecs_task" {
  name = "${local.name_prefix}-ECSTaskRole"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = local.common_tags
}

# S3 Access Policy for Task Role
resource "aws_iam_role_policy" "s3_access" {
  name = "S3Access"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.documents.arn,
          "${aws_s3_bucket.documents.arn}/*"
        ]
      }
    ]
  })
}

# Bedrock Access Policy for Task Role
resource "aws_iam_role_policy" "bedrock_access" {
  name = "BedrockAccess"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream",
          "bedrock:ListFoundationModels",
          "bedrock:GetFoundationModel"
        ]
        Resource = [
          "arn:aws:bedrock:${var.aws_region}::foundation-model/${local.primary_model_id}",
          "arn:aws:bedrock:${var.aws_region}::foundation-model/${local.fast_model_id}",
          "arn:aws:bedrock:${var.aws_region}::foundation-model/${local.embedding_model_id}"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "bedrock:ListFoundationModels"
        ]
        Resource = "*"
      },
      # Bedrock Agent and Knowledge Base permissions (for simplified architecture)
      {
        Effect = "Allow"
        Action = [
          "bedrock-agent:Retrieve",
          "bedrock-agent:RetrieveAndGenerate",
          "bedrock-agent:GetKnowledgeBase",
          "bedrock-agent:ListDataSources",
          "bedrock-agent:GetDataSource",
          "bedrock-agent:StartIngestionJob",
          "bedrock-agent:GetIngestionJob",
          "bedrock-agent:ListIngestionJobs"
        ]
        Resource = [
          "*"  # Allow all Knowledge Base operations - specific ARNs set after manual creation
        ]
      },
      # Bedrock Guardrail permissions
      {
        Effect = "Allow"
        Action = [
          "bedrock:GetGuardrail",
          "bedrock:ApplyGuardrail"
        ]
        Resource = [
          aws_bedrock_guardrail.ncdhhs_content_filter.guardrail_arn
        ]
      },
      # S3 access for Knowledge Base bucket (simplified architecture)
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket",
          "s3:GetBucketLocation",
          "s3:PutObjectMetadata"
        ]
        Resource = [
          aws_s3_bucket.bedrock_knowledge_base.arn,
          "${aws_s3_bucket.bedrock_knowledge_base.arn}/*"
        ]
      },
      # OpenSearch Serverless permissions (if Knowledge Base enabled)
      {
        Effect = "Allow"
        Action = [
          "aoss:APIAccessAll"
        ]
        Resource = [
          "*"  # Allow all OpenSearch operations - specific ARNs set after manual creation
        ]
      }
    ]
  })
}

# Additional CloudWatch Logs permissions for enhanced logging
resource "aws_iam_role_policy" "cloudwatch_logs" {
  name = "CloudWatchLogsAccess"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogStreams"
        ]
        Resource = "${aws_cloudwatch_log_group.ecs.arn}:*"
      }
    ]
  })
}

# OpenSearch Access Policy for Task Role
resource "aws_iam_role_policy" "opensearch_access" {
  name = "OpenSearchAccess"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "es:ESHttpGet",
          "es:ESHttpPost",
          "es:ESHttpPut",
          "es:ESHttpDelete",
          "es:ESHttpHead",
          "es:Describe*",
          "es:List*"
        ]
        Resource = "arn:aws:es:${var.aws_region}:${data.aws_caller_identity.current.account_id}:domain/${var.project_name}-opensearch/*"
      }
    ]
  })
}
