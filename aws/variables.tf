variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "ncdhhs-pdf-qa"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "dev"
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod."
  }
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "aws_profile" {
  description = "AWS profile to use"
  type        = string
  default     = "dhanu_aws"
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "container_cpu" {
  description = "CPU units for the container (1024 = 1 vCPU)"
  type        = number
  default     = 1024
}

variable "container_memory" {
  description = "Memory for the container in MB"
  type        = number
  default     = 2048
}

variable "container_port" {
  description = "Port the container listens on"
  type        = number
  default     = 8000
}

variable "redis_node_type" {
  description = "Redis node type"
  type        = string
  default     = "cache.t3.micro"
}

variable "desired_count" {
  description = "Desired number of ECS tasks"
  type        = number
  default     = 1
}

variable "alb_idle_timeout" {
  description = "ALB idle timeout in seconds for long-running PDF processing"
  type        = number
  default     = 300
}

variable "pdf_download_timeout" {
  description = "PDF download timeout in seconds"
  type        = number
  default     = 180
}

variable "enable_bedrock_models" {
  description = "List of Bedrock models to enable access for"
  type        = list(string)
  default = [
    "anthropic.claude-instant-v1",
    "anthropic.claude-3-haiku-20240307-v1:0", 
    "amazon.titan-text-express-v1",
    "amazon.titan-embed-text-v2:0"
  ]
}

# OpenSearch variables
variable "opensearch_instance_type" {
  description = "OpenSearch instance type"
  type        = string
  default     = "t3.small.search"
}

variable "opensearch_instance_count" {
  description = "Number of OpenSearch instances"
  type        = number
  default     = 1
}

variable "opensearch_volume_size" {
  description = "OpenSearch EBS volume size in GB"
  type        = number
  default     = 20
}
