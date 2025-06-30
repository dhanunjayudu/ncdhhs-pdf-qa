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
          for model in var.enable_bedrock_models :
          "arn:aws:bedrock:${var.aws_region}::foundation-model/${model}"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "bedrock:ListFoundationModels"
        ]
        Resource = "*"
      },
      # Bedrock Agent and Knowledge Base permissions
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
          aws_bedrock_knowledge_base.ncdhhs_pdf_kb.arn,
          "${aws_bedrock_knowledge_base.ncdhhs_pdf_kb.arn}/*",
          aws_bedrock_data_source.ncdhhs_pdf_documents.arn
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
      # S3 access for Knowledge Base bucket
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.bedrock_knowledge_base.arn,
          "${aws_s3_bucket.bedrock_knowledge_base.arn}/*"
        ]
      },
      # OpenSearch Serverless permissions
      {
        Effect = "Allow"
        Action = [
          "aoss:APIAccessAll"
        ]
        Resource = [
          aws_opensearchserverless_collection.bedrock_knowledge_base.arn
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
