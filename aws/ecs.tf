# ECS Cluster
resource "aws_ecs_cluster" "main" {
  name = "${local.name_prefix}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-cluster"
  })
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "ecs" {
  name              = "/ecs/${local.name_prefix}-backend"
  retention_in_days = 7

  tags = local.common_tags
}

# ECS Task Definition
resource "aws_ecs_task_definition" "backend" {
  family                   = "${local.name_prefix}-backend"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.container_cpu
  memory                   = var.container_memory
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn           = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name  = "${local.name_prefix}-backend"
      image = "${local.account_id}.dkr.ecr.${var.aws_region}.amazonaws.com/${local.name_prefix}-backend:latest"
      
      portMappings = [
        {
          containerPort = var.container_port
          hostPort      = var.container_port
          protocol      = "tcp"
        }
      ]
      
      environment = [
        {
          name  = "S3_BUCKET_NAME"
          value = aws_s3_bucket.documents.bucket
        },
        {
          name  = "AWS_REGION"
          value = var.aws_region
        },
        {
          name  = "REDIS_URL"
          value = "redis://${aws_elasticache_replication_group.redis.primary_endpoint_address}:6379"
        },
        # OpenSearch configuration
        {
          name  = "OPENSEARCH_ENDPOINT"
          value = "https://${aws_opensearch_domain.ncdhhs_vector_search.endpoint}"
        },
        {
          name  = "OPENSEARCH_INDEX"
          value = "ncdhhs-documents"
        },
        # Container environment detection
        {
          name  = "AWS_EXECUTION_ENV"
          value = "AWS_ECS_FARGATE"
        },
        # Disable AWS profile usage in container
        {
          name  = "AWS_CONFIG_FILE"
          value = "/dev/null"
        },
        {
          name  = "AWS_SHARED_CREDENTIALS_FILE"
          value = "/dev/null"
        },
        # PDF processing configuration
        {
          name  = "PDF_DOWNLOAD_TIMEOUT"
          value = tostring(var.pdf_download_timeout)
        }
      ]
      
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.ecs.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }
      
      essential = true
      
      # Health check configuration
      healthCheck = {
        command = ["CMD-SHELL", "curl -f http://localhost:${var.container_port}/health || exit 1"]
        interval = 30
        timeout = 5
        retries = 3
        startPeriod = 60
      }
    }
  ])

  tags = local.common_tags
}

# ECS Service
resource "aws_ecs_service" "backend" {
  name            = "${local.name_prefix}-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.backend.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.public[*].id
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.backend.arn
    container_name   = "${local.name_prefix}-backend"
    container_port   = var.container_port
  }

  depends_on = [aws_lb_listener.backend]

  tags = local.common_tags
}
