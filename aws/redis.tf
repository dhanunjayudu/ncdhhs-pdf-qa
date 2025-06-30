# Redis Subnet Group
resource "aws_elasticache_subnet_group" "redis" {
  name       = "${local.name_prefix}-redis-subnet-group"
  subnet_ids = aws_subnet.private[*].id

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-redis-subnet-group"
  })
}

# Redis Cluster
resource "aws_elasticache_replication_group" "redis" {
  replication_group_id         = "${local.name_prefix}-redis"
  description                  = "Redis cluster for ${local.name_prefix}"
  
  node_type                    = var.redis_node_type
  port                         = 6379
  parameter_group_name         = "default.redis7"
  
  num_cache_clusters           = 1
  
  subnet_group_name            = aws_elasticache_subnet_group.redis.name
  security_group_ids           = [aws_security_group.redis.id]
  
  at_rest_encryption_enabled   = true
  transit_encryption_enabled   = false  # Disabled for simplicity, enable in production
  
  automatic_failover_enabled   = false  # Single node setup
  multi_az_enabled            = false   # Single node setup

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-redis"
  })
}
