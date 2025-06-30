# OpenSearch Domain for Vector Search
resource "aws_opensearch_domain" "ncdhhs_vector_search" {
  domain_name    = "${var.project_name}-opensearch"
  engine_version = "OpenSearch_2.11"

  cluster_config {
    instance_type            = var.opensearch_instance_type
    instance_count           = var.opensearch_instance_count
    dedicated_master_enabled = false
    zone_awareness_enabled   = false
  }

  ebs_options {
    ebs_enabled = true
    volume_type = "gp3"
    volume_size = var.opensearch_volume_size
  }

  vpc_options {
    subnet_ids         = [aws_subnet.private[0].id]
    security_group_ids = [aws_security_group.opensearch_sg.id]
  }

  domain_endpoint_options {
    enforce_https       = true
    tls_security_policy = "Policy-Min-TLS-1-2-2019-07"
  }

  encrypt_at_rest {
    enabled = true
  }

  node_to_node_encryption {
    enabled = true
  }

  advanced_security_options {
    enabled                        = false
    anonymous_auth_enabled         = false
    internal_user_database_enabled = false
  }

  access_policies = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          AWS = [
            aws_iam_role.ecs_task.arn,
            aws_iam_role.opensearch_role.arn
          ]
        }
        Action   = "es:*"
        Resource = "arn:aws:es:${var.aws_region}:${data.aws_caller_identity.current.account_id}:domain/${var.project_name}-opensearch/*"
      }
    ]
  })

  tags = {
    Name        = "${var.project_name}-opensearch"
    Environment = var.environment
    Project     = var.project_name
  }

  depends_on = [aws_iam_service_linked_role.opensearch]
}

# Service-linked role for OpenSearch (not serverless)
resource "aws_iam_service_linked_role" "opensearch" {
  aws_service_name = "es.amazonaws.com"
  description      = "Service-linked role for OpenSearch"

  lifecycle {
    ignore_changes = [aws_service_name]
  }
}

# IAM role for OpenSearch access
resource "aws_iam_role" "opensearch_role" {
  name = "${var.project_name}-opensearch-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "opensearch.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "${var.project_name}-opensearch-role"
    Environment = var.environment
    Project     = var.project_name
  }
}

# Security group for OpenSearch
resource "aws_security_group" "opensearch_sg" {
  name_prefix = "${var.project_name}-opensearch-"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.project_name}-opensearch-sg"
    Environment = var.environment
    Project     = var.project_name
  }
}

# Note: aws_caller_identity data source is already defined in main.tf
