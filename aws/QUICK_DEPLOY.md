# Quick Deployment Guide - Fixed Configuration

## ✅ **Issues Resolved:**
- ❌ ~~Unresolved reference `primary_model_id` error~~ → ✅ **FIXED**
- ❌ ~~Invalid PII entity type `SSN`~~ → ✅ **FIXED** (now `US_SOCIAL_SECURITY_NUMBER`)
- ❌ ~~Unsupported Knowledge Base resources~~ → ✅ **FIXED** (using core Bedrock features)
- ❌ ~~Missing random provider~~ → ✅ **FIXED**

## 🚀 **Ready to Deploy:**

### **1. Choose Your Model Preference:**
Edit `terraform.tfvars`:
```hcl
# Recommended for your case (since Claude 3 unavailable)
bedrock_model_preference = "nova"  # or "titan", "claude2"
```

### **2. Deploy Infrastructure:**
```bash
cd aws/
./deploy-bedrock.sh
```

### **3. Enable Models in AWS Console:**
After deployment, enable these models in [Bedrock Console](https://console.aws.amazon.com/bedrock/home?region=us-east-1#/modelaccess):

**For Nova (recommended):**
- ✅ `amazon.nova-pro-v1:0`
- ✅ `amazon.nova-lite-v1:0`
- ✅ `amazon.titan-embed-text-v2:0`

**For Titan:**
- ✅ `amazon.titan-text-premier-v1:0`
- ✅ `amazon.titan-text-express-v1`
- ✅ `amazon.titan-embed-text-v2:0`

**For Claude 2:**
- ✅ `anthropic.claude-v2:1`
- ✅ `anthropic.claude-instant-v1`
- ✅ `amazon.titan-embed-text-v2:0`

## 🎯 **What Gets Created:**

### **✅ Core Bedrock Features:**
- **Content Guardrails** with PII filtering
- **S3 Bucket** for document storage
- **CloudWatch Dashboard** for monitoring
- **IAM Roles** with proper permissions
- **Environment Variables** for your backend

### **🔧 Backend Integration:**
Your ECS tasks will have these environment variables:
```bash
BEDROCK_GUARDRAIL_ID=your-guardrail-id
BEDROCK_GUARDRAIL_VERSION=1
S3_KNOWLEDGE_BASE_BUCKET=your-bucket-name
BEDROCK_PRIMARY_MODEL=amazon.nova-pro-v1:0
BEDROCK_FAST_MODEL=amazon.nova-lite-v1:0
BEDROCK_EMBEDDING_MODEL=amazon.titan-embed-text-v2:0
```

## 🧪 **Test Your Setup:**

### **1. Test Model Access:**
```bash
aws bedrock invoke-model \
  --model-id amazon.nova-pro-v1:0 \
  --body '{"messages":[{"role":"user","content":"Hello"}],"max_tokens":100}' \
  --cli-binary-format raw-in-base64-out \
  --region us-east-1 \
  test-output.json

cat test-output.json
```

### **2. Upload Test Documents:**
```bash
# Get bucket name from Terraform output
BUCKET=$(terraform output -raw bedrock_s3_bucket)

# Upload your PDFs
aws s3 cp your-pdfs/ s3://$BUCKET/documents/ --recursive
```

### **3. Test Guardrails:**
The guardrails will automatically filter:
- Medical advice requests
- Personal health information
- Inappropriate content
- PII data (emails, phone numbers, SSNs)

## 💡 **Key Differences from Full Version:**

### **What's Working:**
- ✅ Model selection and configuration
- ✅ Content guardrails and safety
- ✅ S3 document storage
- ✅ Monitoring and logging
- ✅ Proper IAM permissions

### **What's Simplified:**
- 📝 Manual document indexing (instead of automatic Knowledge Base)
- 🔍 Your backend handles search logic (instead of Bedrock Agent)
- 📊 Direct model invocation (instead of Knowledge Base queries)

## 🔄 **Next Steps:**

1. **Deploy the infrastructure** with `./deploy-bedrock.sh`
2. **Enable the models** in AWS Console
3. **Update your backend** to use the new environment variables
4. **Test the enhanced Q&A** functionality
5. **Upload documents** to the S3 bucket

## 🆘 **If You Need Full Knowledge Base:**

The full Knowledge Base features might be available in newer AWS provider versions. Check:
```bash
terraform providers
```

If you have AWS provider >= 5.30, you can try the full version in `bedrock-full.tf.backup`.

---

**Your enhanced NCDHHS PDF Q&A system is ready to deploy! 🎉**
