# Bedrock Model Selection Guide

Since you cannot enable Claude 3 models, here are the available alternatives with their trade-offs:

## 🎯 **Recommended Model Options**

### **Option 1: Amazon Nova Models (RECOMMENDED)**
```hcl
bedrock_model_preference = "nova"
```

**Models Used:**
- **Primary**: `amazon.nova-pro-v1:0` - High quality Q&A
- **Fast**: `amazon.nova-lite-v1:0` - Quick responses
- **Embedding**: `amazon.titan-embed-text-v2:0` - Latest embeddings

**Pros:**
- ✅ Latest generation models (2024)
- ✅ Cost-effective pricing
- ✅ Good performance for Q&A tasks
- ✅ Built by Amazon, well-integrated

**Cons:**
- ⚠️ Newer models, less community feedback

**Pricing (approximate):**
- Nova Pro: ~$0.80 per 1M input tokens, ~$3.20 per 1M output tokens
- Nova Lite: ~$0.06 per 1M input tokens, ~$0.24 per 1M output tokens

---

### **Option 2: Amazon Titan Models**
```hcl
bedrock_model_preference = "titan"
```

**Models Used:**
- **Primary**: `amazon.titan-text-premier-v1:0` - High quality
- **Fast**: `amazon.titan-text-express-v1` - Fast responses
- **Embedding**: `amazon.titan-embed-text-v2:0` - Latest embeddings

**Pros:**
- ✅ Proven reliability
- ✅ Good integration with AWS services
- ✅ Moderate pricing
- ✅ Well-documented

**Cons:**
- ⚠️ May not be as sophisticated as Claude models

**Pricing (approximate):**
- Titan Premier: ~$0.50 per 1M input tokens, ~$1.50 per 1M output tokens
- Titan Express: ~$0.20 per 1M input tokens, ~$0.60 per 1M output tokens

---

### **Option 3: Claude 2 Models**
```hcl
bedrock_model_preference = "claude2"
```

**Models Used:**
- **Primary**: `anthropic.claude-v2:1` - High quality responses
- **Fast**: `anthropic.claude-instant-v1` - Quick responses
- **Embedding**: `amazon.titan-embed-text-v2:0` - Latest embeddings

**Pros:**
- ✅ Excellent for complex reasoning
- ✅ Good safety features
- ✅ Well-tested in production
- ✅ Strong performance on Q&A tasks

**Cons:**
- ⚠️ Higher cost than Amazon models
- ⚠️ Older generation than Claude 3

**Pricing (approximate):**
- Claude v2.1: ~$8.00 per 1M input tokens, ~$24.00 per 1M output tokens
- Claude Instant: ~$0.80 per 1M input tokens, ~$2.40 per 1M output tokens

---

### **Option 4: Claude 3 Models (If Available)**
```hcl
bedrock_model_preference = "claude3"
```

**Models Used:**
- **Primary**: `anthropic.claude-3-sonnet-20240229-v1:0`
- **Fast**: `anthropic.claude-3-haiku-20240307-v1:0`
- **Embedding**: `amazon.titan-embed-text-v1`

**Note**: Only use this if you can enable Claude 3 models in your console.

---

## 🔧 **How to Change Model Preference**

### **1. Update terraform.tfvars:**
```hcl
bedrock_model_preference = "nova"  # or "titan", "claude2", "claude3"
```

### **2. Apply changes:**
```bash
cd aws/
terraform plan
terraform apply
```

### **3. Enable models in AWS Console:**
After deployment, enable the specific models in the [Bedrock Console](https://console.aws.amazon.com/bedrock/home?region=us-east-1#/modelaccess).

---

## 🧪 **Testing Model Availability**

### **Check what models you can enable:**
```bash
# List all available text models
aws bedrock list-foundation-models \
  --region us-east-1 \
  --query 'modelSummaries[?contains(outputModalities, `TEXT`)].{ModelId:modelId,ModelName:modelName,Provider:providerName}' \
  --output table

# Check specific model availability
aws bedrock get-foundation-model \
  --model-identifier amazon.nova-pro-v1:0 \
  --region us-east-1
```

### **Test model access after enabling:**
```bash
# Test Nova Pro
aws bedrock invoke-model \
  --model-id amazon.nova-pro-v1:0 \
  --body '{"messages":[{"role":"user","content":"Hello, can you help me?"}],"max_tokens":100}' \
  --cli-binary-format raw-in-base64-out \
  --region us-east-1 \
  output.json

# Check the response
cat output.json
```

---

## 💰 **Cost Comparison**

| Model Set | Input Cost (per 1M tokens) | Output Cost (per 1M tokens) | Best For |
|-----------|----------------------------|------------------------------|----------|
| **Nova** | $0.06 - $0.80 | $0.24 - $3.20 | Cost-effective, modern |
| **Titan** | $0.20 - $0.50 | $0.60 - $1.50 | Reliable, AWS-native |
| **Claude 2** | $0.80 - $8.00 | $2.40 - $24.00 | Complex reasoning |
| **Claude 3** | $0.25 - $3.00 | $1.25 - $15.00 | Latest features (if available) |

---

## 🎯 **Recommendation for NCDHHS**

**Start with Nova models** (`bedrock_model_preference = "nova"`):

1. **Cost-effective** for government budgets
2. **Latest technology** from Amazon
3. **Good performance** for document Q&A
4. **Easy to enable** in most AWS accounts

If Nova models don't meet your quality requirements, try **Titan models** as they're reliable and well-integrated with AWS services.

---

## 🔄 **Migration Path**

You can easily switch between model sets:

1. **Update** `terraform.tfvars`
2. **Run** `terraform apply`
3. **Enable** new models in console
4. **Test** the application
5. **Rollback** if needed by changing the preference back

The infrastructure supports all model types, so switching is seamless!

---

## 🆘 **Troubleshooting**

### **Model Not Available Error:**
```
Error: You don't have access to the model
```
**Solution**: Enable the model in [Bedrock Console](https://console.aws.amazon.com/bedrock/home?region=us-east-1#/modelaccess)

### **Model Selection Not Working:**
```
Error: Invalid model preference
```
**Solution**: Check that `bedrock_model_preference` is one of: `nova`, `titan`, `claude2`, `claude3`

### **High Costs:**
**Solution**: Switch to Nova or Titan models for lower costs, or implement request caching.
