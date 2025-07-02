# Update outputs with actual Knowledge Base IDs
locals {
  bedrock_knowledge_base_id = "EJRS8I2F6J"
  bedrock_data_source_id    = "PGYK8O2WDY"
  opensearch_collection_arn = "arn:aws:aoss:us-east-1:942713336312:collection/14dzr3m6d071boqiytt6"
}

# Update the bedrock configuration output
output "bedrock_configuration_updated" {
  description = "Updated Bedrock configuration with actual Knowledge Base"
  value = {
    architecture           = "Complete S3 + Bedrock Knowledge Base"
    knowledge_base_id      = local.bedrock_knowledge_base_id
    data_source_id         = local.bedrock_data_source_id
    opensearch_collection_arn = local.opensearch_collection_arn
    s3_bucket             = aws_s3_bucket.bedrock_knowledge_base.id
    embedding_model_id    = "amazon.titan-embed-text-v2:0"
    primary_model_id      = "amazon.nova-pro-v1:0"
    fast_model_id         = "amazon.nova-lite-v1:0"
    guardrail_id          = aws_bedrock_guardrail.ncdhhs_content_filter.guardrail_id
    guardrail_version     = aws_bedrock_guardrail.ncdhhs_content_filter.version
    region                = var.aws_region
    status                = "ACTIVE"
  }
}

# Updated environment variables for ECS
output "bedrock_environment_variables_updated" {
  description = "Updated environment variables for ECS with actual Knowledge Base IDs"
  value = {
    AWS_REGION                    = var.aws_region
    BEDROCK_KNOWLEDGE_BASE_ID     = local.bedrock_knowledge_base_id
    BEDROCK_DATA_SOURCE_ID        = local.bedrock_data_source_id
    BEDROCK_PRIMARY_MODEL         = "amazon.nova-pro-v1:0"
    BEDROCK_FAST_MODEL           = "amazon.nova-lite-v1:0"
    BEDROCK_EMBEDDING_MODEL      = "amazon.titan-embed-text-v2:0"
    BEDROCK_GUARDRAIL_ID         = aws_bedrock_guardrail.ncdhhs_content_filter.guardrail_id
    BEDROCK_GUARDRAIL_VERSION    = aws_bedrock_guardrail.ncdhhs_content_filter.version
    S3_KNOWLEDGE_BASE_BUCKET     = aws_s3_bucket.bedrock_knowledge_base.id
    OPENSEARCH_COLLECTION_ARN    = local.opensearch_collection_arn
  }
}

# Final setup completion status
output "bedrock_setup_final" {
  description = "Final Bedrock Knowledge Base setup status"
  value = {
    status = "COMPLETE"
    architecture = "Full S3 + Bedrock Knowledge Base + OpenSearch Serverless"
    message = "🎉 Bedrock Knowledge Base successfully created and tested!"
    
    knowledge_base = {
      id = local.bedrock_knowledge_base_id
      name = "ncdhhs-pdf-qa-knowledge-base"
      status = "ACTIVE"
    }
    
    data_source = {
      id = local.bedrock_data_source_id
      name = "ncdhhs-pdf-documents"
      s3_uri = "s3://${aws_s3_bucket.bedrock_knowledge_base.id}/documents/"
    }
    
    vector_store = {
      collection_arn = local.opensearch_collection_arn
      index_name = "bedrock-kb-faiss-index"
      engine = "FAISS"
      dimensions = 1024
    }
    
    next_steps = [
      "1. ✅ Knowledge Base created and tested",
      "2. ✅ Test document uploaded and indexed",
      "3. ✅ Retrieval working correctly",
      "4. 🔄 Update ECS backend with new environment variables",
      "5. 🔄 Deploy updated backend container",
      "6. 🔄 Test full Q&A functionality via frontend",
      "7. 📁 Upload actual NCDHHS PDF documents",
      "8. 🧪 Test with real documents and queries"
    ]
    
    console_urls = {
      knowledge_base = "https://us-east-1.console.aws.amazon.com/bedrock/home?region=us-east-1#/knowledge-bases/EJRS8I2F6J"
      s3_bucket = "https://s3.console.aws.amazon.com/s3/buckets/${aws_s3_bucket.bedrock_knowledge_base.id}"
      opensearch_collection = "https://us-east-1.console.aws.amazon.com/aos/home?region=us-east-1#opensearch/collections/14dzr3m6d071boqiytt6"
    }
  }
}
