# NC DHHS PDF Q&A - Deployment Guide

This guide covers the complete deployment process including all the optimizations and fixes implemented during development.

## 🚀 Complete Deployment Process

### Phase 1: Infrastructure Setup

1. **Initialize Terraform:**
   ```bash
   cd aws
   ./deploy.sh init
   ```

2. **Review and Deploy:**
   ```bash
   ./deploy.sh plan
   ./deploy.sh apply
   ```

### Phase 2: Bedrock Model Access

**CRITICAL:** Enable Bedrock models before application deployment:

1. **Go to AWS Bedrock Console:**
   ```
   https://us-east-1.console.aws.amazon.com/bedrock/home?region=us-east-1#/modelaccess
   ```

2. **Enable These Models:**
   - ✅ **Claude Instant** (`anthropic.claude-instant-v1`)
   - ✅ **Claude 3 Haiku** (`anthropic.claude-3-haiku-20240307-v1:0`)
   - ✅ **Titan Text Express** (`amazon.titan-text-express-v1`) - **Currently Working**
   - ✅ **Titan Embeddings v2** (`amazon.titan-embed-text-v2:0`)

3. **Verify Access:**
   ```bash
   aws bedrock-runtime invoke-model \
     --model-id "amazon.titan-text-express-v1" \
     --body '{"inputText":"Hello","textGenerationConfig":{"maxTokenCount":10}}' \
     --profile dhanu_aws --region us-east-1 /tmp/test.json
   ```

### Phase 3: Container Deployment

1. **Build Container:**
   ```bash
   cd ../backend
   docker build -t ncdhhs-pdf-qa-backend .
   ```

2. **Push to ECR:**
   ```bash
   # Get ECR login
   aws ecr get-login-password --region us-east-1 --profile dhanu_aws | \
     docker login --username AWS --password-stdin \
     942713336312.dkr.ecr.us-east-1.amazonaws.com

   # Tag and push
   docker tag ncdhhs-pdf-qa-backend:latest \
     942713336312.dkr.ecr.us-east-1.amazonaws.com/ncdhhs-pdf-qa-dev-backend:latest
   docker push 942713336312.dkr.ecr.us-east-1.amazonaws.com/ncdhhs-pdf-qa-dev-backend:latest
   ```

3. **Deploy to ECS:**
   ```bash
   aws ecs update-service \
     --cluster ncdhhs-pdf-qa-dev-cluster \
     --service ncdhhs-pdf-qa-dev-service \
     --force-new-deployment \
     --profile dhanu_aws --region us-east-1
   ```

### Phase 4: Verification

1. **Check Service Health:**
   ```bash
   curl http://ncdhhs-pdf-qa-dev-alb-940310890.us-east-1.elb.amazonaws.com/health
   ```

2. **Test PDF Processing:**
   ```bash
   curl -X POST "http://ncdhhs-pdf-qa-dev-alb-940310890.us-east-1.elb.amazonaws.com/process-pdf-batch" \
     -H "Content-Type: application/json" \
     -d '{
       "pdf_links": [
         {
           "title": "Test Document",
           "url": "https://www.orimi.com/pdf-test.pdf"
         }
       ]
     }'
   ```

3. **Test AI Q&A:**
   ```bash
   curl -X POST "http://ncdhhs-pdf-qa-dev-alb-940310890.us-east-1.elb.amazonaws.com/ask-question" \
     -H "Content-Type: application/json" \
     -d '{
       "question": "What is this document about?"
     }'
   ```

## 🔧 Key Infrastructure Changes Made

### 1. Load Balancer Optimizations
- **ALB Timeout**: Increased from 60s to 300s (5 minutes)
- **Reason**: Large PDF processing can take longer than default timeout
- **Terraform**: `idle_timeout = var.alb_idle_timeout`

### 2. Container Authentication Fixes
- **Environment Variables**: Added container detection variables
- **AWS Profile Isolation**: Disabled profile usage in containers
- **IAM Role Usage**: Forced container to use IAM roles only

```hcl
environment = [
  {
    name  = "AWS_EXECUTION_ENV"
    value = "AWS_ECS_FARGATE"
  },
  {
    name  = "AWS_CONFIG_FILE"
    value = "/dev/null"
  },
  {
    name  = "AWS_SHARED_CREDENTIALS_FILE"
    value = "/dev/null"
  }
]
```

### 3. Enhanced IAM Permissions
- **Bedrock Access**: Added comprehensive Bedrock model permissions
- **CloudWatch Logs**: Enhanced logging permissions
- **S3 Access**: Maintained document storage permissions

### 4. PDF Processing Optimizations
- **Download Timeout**: Increased from 60s to 180s (3 minutes)
- **Application Timeout**: Configurable via environment variables
- **Error Handling**: Improved timeout and retry logic

### 5. Health Monitoring
- **Container Health Checks**: Added proper health check configuration
- **CloudWatch Dashboard**: Bedrock usage monitoring
- **Enhanced Logging**: Better error tracking and debugging

## 🐛 Issues Resolved

### Issue 1: AWS Profile Authentication in Containers
**Problem**: Container tried to use local AWS profile (`dhanu_aws`)
**Solution**: 
- Added environment variables to disable profile usage
- Implemented conditional authentication logic
- Used IAM roles exclusively in containers

### Issue 2: Load Balancer Timeouts
**Problem**: 504 Gateway Timeout for large PDF processing
**Solution**:
- Increased ALB idle timeout to 300 seconds
- Increased PDF download timeout to 180 seconds
- Added proper timeout configuration in Terraform

### Issue 3: Bedrock Model Access
**Problem**: AccessDeniedException for Bedrock models
**Solution**:
- Manual model enablement in AWS Console
- Enhanced IAM permissions for specific models
- Implemented model fallback logic (Titan → Claude)

### Issue 4: Container Startup Issues
**Problem**: Container authentication failures
**Solution**:
- Created separate container entry point (`main_container.py`)
- Added container environment detection
- Implemented clean session management

## 📊 Current System Status

### ✅ Working Components:
- **ECS Service**: Running and healthy
- **Load Balancer**: Operational with extended timeout
- **S3 Storage**: Documents stored successfully
- **Bedrock Integration**: Titan Text Express working
- **Q&A Functionality**: AI responses working perfectly
- **PDF Processing**: Handles various document sizes

### 🔄 Performance Metrics:
- **PDF Processing**: 1-3 minutes for typical documents
- **Q&A Response**: 1-2 seconds
- **System Uptime**: Stable with proper health checks
- **Error Rate**: Low with proper fallback mechanisms

### 💰 Cost Optimization:
- **Fargate**: Pay-per-use container execution
- **Bedrock**: Pay-per-token AI usage
- **S3**: Efficient document storage
- **Redis**: Single node for development

## 🚨 Production Readiness Checklist

- [x] Infrastructure as Code (Terraform)
- [x] Container Security (non-root user)
- [x] IAM Least Privilege
- [x] Encryption at Rest (S3, Redis)
- [x] Health Monitoring
- [x] Error Handling & Logging
- [x] Timeout Configuration
- [x] AI Model Integration
- [ ] HTTPS/SSL Certificate (for production)
- [ ] Multi-AZ Deployment (for production)
- [ ] Backup Strategy (for production)
- [ ] Monitoring Alerts (for production)

## 🔍 Monitoring & Troubleshooting

### CloudWatch Logs:
```bash
aws logs get-log-events \
  --log-group-name /ecs/ncdhhs-pdf-qa-dev-backend \
  --log-stream-name ecs/ncdhhs-pdf-qa-dev-backend/[TASK-ID] \
  --profile dhanu_aws --region us-east-1
```

### ECS Service Status:
```bash
aws ecs describe-services \
  --cluster ncdhhs-pdf-qa-dev-cluster \
  --services ncdhhs-pdf-qa-dev-service \
  --profile dhanu_aws --region us-east-1
```

### Bedrock Model Testing:
```bash
# Test script available at /tmp/test-bedrock-access.sh
/tmp/test-bedrock-access.sh
```

## 📝 Next Steps for Production

1. **Enable HTTPS** with ACM certificate
2. **Set up CloudWatch Alarms** for monitoring
3. **Implement backup strategy** for S3 and Redis
4. **Add WAF protection** for security
5. **Enable Multi-AZ** for high availability
6. **Set up CI/CD pipeline** for automated deployments

The system is now **fully operational** and ready for NC DHHS document processing and AI-powered Q&A functionality! 🎉
