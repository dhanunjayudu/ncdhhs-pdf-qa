output "vpc_id" {
  description = "ID of the VPC"
  value       = aws_vpc.main.id
}

output "public_subnet_ids" {
  description = "IDs of the public subnets"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "IDs of the private subnets"
  value       = aws_subnet.private[*].id
}

output "ecs_cluster_name" {
  description = "Name of the ECS cluster"
  value       = aws_ecs_cluster.main.name
}

output "ecs_cluster_arn" {
  description = "ARN of the ECS cluster"
  value       = aws_ecs_cluster.main.arn
}

output "alb_dns_name" {
  description = "DNS name of the load balancer"
  value       = aws_lb.main.dns_name
}

output "alb_zone_id" {
  description = "Zone ID of the load balancer"
  value       = aws_lb.main.zone_id
}

output "alb_idle_timeout" {
  description = "ALB idle timeout in seconds"
  value       = aws_lb.main.idle_timeout
}

output "s3_bucket_name" {
  description = "Name of the S3 bucket"
  value       = aws_s3_bucket.documents.bucket
}

output "s3_bucket_arn" {
  description = "ARN of the S3 bucket"
  value       = aws_s3_bucket.documents.arn
}

output "redis_endpoint" {
  description = "Redis cluster endpoint"
  value       = aws_elasticache_replication_group.redis.primary_endpoint_address
}

output "redis_port" {
  description = "Redis cluster port"
  value       = aws_elasticache_replication_group.redis.port
}

output "ecr_repository_url" {
  description = "URL of the ECR repository"
  value       = aws_ecr_repository.backend.repository_url
}

output "ecs_task_execution_role_arn" {
  description = "ARN of the ECS task execution role"
  value       = aws_iam_role.ecs_task_execution.arn
}

output "ecs_task_role_arn" {
  description = "ARN of the ECS task role"
  value       = aws_iam_role.ecs_task.arn
}

output "target_group_arn" {
  description = "ARN of the target group"
  value       = aws_lb_target_group.backend.arn
}

output "ecs_security_group_id" {
  description = "ID of the ECS security group"
  value       = aws_security_group.ecs.id
}

output "application_url" {
  description = "URL to access the application"
  value       = "http://${aws_lb.main.dns_name}"
}

output "bedrock_enabled_models" {
  description = "List of Bedrock models enabled for access"
  value       = var.enable_bedrock_models
}

output "cloudwatch_log_group" {
  description = "CloudWatch log group for ECS tasks"
  value       = aws_cloudwatch_log_group.ecs.name
}

output "pdf_processing_config" {
  description = "PDF processing configuration"
  value = {
    alb_timeout         = var.alb_idle_timeout
    download_timeout    = var.pdf_download_timeout
    container_cpu       = var.container_cpu
    container_memory    = var.container_memory
  }
}

output "opensearch_endpoint" {
  description = "OpenSearch domain endpoint"
  value       = aws_opensearch_domain.ncdhhs_vector_search.endpoint
}

output "opensearch_domain_arn" {
  description = "OpenSearch domain ARN"
  value       = aws_opensearch_domain.ncdhhs_vector_search.arn
}

output "opensearch_kibana_endpoint" {
  description = "OpenSearch Kibana endpoint"
  value       = aws_opensearch_domain.ncdhhs_vector_search.kibana_endpoint
}

output "vector_database_config" {
  description = "Vector database configuration"
  value = {
    opensearch_endpoint     = aws_opensearch_domain.ncdhhs_vector_search.endpoint
    opensearch_index       = "ncdhhs-documents"
    instance_type          = var.opensearch_instance_type
    instance_count         = var.opensearch_instance_count
    volume_size           = var.opensearch_volume_size
  }
}

# Bedrock Core Outputs (without Knowledge Base resources)
output "bedrock_guardrail_id" {
  description = "ID of the Bedrock Guardrail"
  value       = aws_bedrock_guardrail.ncdhhs_content_filter.guardrail_id
}

output "bedrock_guardrail_version" {
  description = "Version of the Bedrock Guardrail"
  value       = aws_bedrock_guardrail.ncdhhs_content_filter.version
}

output "bedrock_s3_bucket" {
  description = "S3 bucket for Bedrock Knowledge Base documents"
  value       = aws_s3_bucket.bedrock_knowledge_base.bucket
}

output "bedrock_s3_bucket_arn" {
  description = "ARN of the S3 bucket for Bedrock Knowledge Base"
  value       = aws_s3_bucket.bedrock_knowledge_base.arn
}

output "bedrock_configuration" {
  description = "Core Bedrock configuration for application"
  value = {
    guardrail_id         = aws_bedrock_guardrail.ncdhhs_content_filter.guardrail_id
    guardrail_version    = aws_bedrock_guardrail.ncdhhs_content_filter.version
    s3_bucket           = aws_s3_bucket.bedrock_knowledge_base.bucket
    models_enabled      = var.bedrock_models_to_enable[var.bedrock_model_preference]
    region             = var.aws_region
    primary_model_id   = local.primary_model_id
    fast_model_id      = local.fast_model_id
    embedding_model_id = local.embedding_model_id
  }
}

output "bedrock_environment_variables" {
  description = "Environment variables for backend application"
  value = {
    BEDROCK_GUARDRAIL_ID     = aws_bedrock_guardrail.ncdhhs_content_filter.guardrail_id
    BEDROCK_GUARDRAIL_VERSION = aws_bedrock_guardrail.ncdhhs_content_filter.version
    S3_KNOWLEDGE_BASE_BUCKET = aws_s3_bucket.bedrock_knowledge_base.bucket
    AWS_REGION              = var.aws_region
    BEDROCK_PRIMARY_MODEL   = local.primary_model_id
    BEDROCK_FAST_MODEL      = local.fast_model_id
    BEDROCK_EMBEDDING_MODEL = local.embedding_model_id
  }
  sensitive = false
}

output "bedrock_setup_complete" {
  description = "Confirmation that core Bedrock infrastructure is set up"
  value = {
    status = "complete"
    message = "Core Bedrock Guardrails and supporting infrastructure have been created successfully"
    next_steps = [
      "1. Enable model access in AWS Bedrock Console",
      "2. Upload documents to S3 bucket: ${aws_s3_bucket.bedrock_knowledge_base.bucket}/documents/",
      "3. Update backend environment variables",
      "4. Test the enhanced Q&A functionality"
    ]
    console_urls = {
      bedrock_console = "https://${var.aws_region}.console.aws.amazon.com/bedrock/home?region=${var.aws_region}"
      s3_bucket = "https://s3.console.aws.amazon.com/s3/buckets/${aws_s3_bucket.bedrock_knowledge_base.bucket}"
    }
    models_to_enable = [
      local.primary_model_id,
      local.fast_model_id,
      local.embedding_model_id
    ]
  }
}
