variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "knowledge_base_name" {
  description = "Name for the Bedrock Knowledge Base"
  type        = string
  default     = "ncdhhs-pdf-knowledge-base"
}

variable "guardrail_name" {
  description = "Name for the Bedrock Guardrail"
  type        = string
  default     = "ncdhhs-content-guardrail"
}

variable "opensearch_collection_name" {
  description = "Name for the OpenSearch Serverless collection"
  type        = string
  default     = "ncdhhs-knowledge-base"
}

variable "embedding_model_arn" {
  description = "ARN of the embedding model to use"
  type        = string
  default     = "arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-embed-text-v1"
}

variable "chunk_size" {
  description = "Maximum tokens per chunk for document processing"
  type        = number
  default     = 512
}

variable "chunk_overlap_percentage" {
  description = "Percentage overlap between chunks"
  type        = number
  default     = 20
}
