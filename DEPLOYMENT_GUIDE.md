# NCDHHS PDF Q&A System - Deployment Guide

## 🏠 **Local Development**

### **Quick Start**
```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Start development server
npm start
```

**Access**: `http://localhost:3000`

### **Local Testing Checklist**
- [ ] Knowledge Base status shows "ACTIVE"
- [ ] Can ask questions and get AI responses
- [ ] PDF processing interface works
- [ ] Real-time status updates function

---

## ☁️ **AWS Amplify Deployment**

### **Method 1: Amplify Console (Recommended)**

#### **Step 1: Prepare Repository**
```bash
# Initialize git repository
git init
git add .
git commit -m "Initial commit - NCDHHS PDF Q&A System"

# Push to GitHub/GitLab
git remote add origin <your-repo-url>
git push -u origin main
```

#### **Step 2: Deploy via Console**
1. **Go to**: [AWS Amplify Console](https://console.aws.amazon.com/amplify/)
2. **Click**: "New app" → "Host web app"
3. **Connect**: Your Git repository
4. **Configure Build**:
   - **Build command**: `npm run build`
   - **Build output directory**: `build`
   - **Base directory**: `frontend`

#### **Step 3: Environment Variables**
Add in Amplify Console:
```
REACT_APP_API_URL = http://ncdhhs-pdf-qa-dev-alb-940310890.us-east-1.elb.amazonaws.com
REACT_APP_ENVIRONMENT = production
REACT_APP_VERSION = 4.0.0
```

#### **Step 4: Build Settings**
Use the provided `amplify.yml`:
```yaml
version: 1
applications:
  - frontend:
      phases:
        preBuild:
          commands:
            - cd frontend
            - npm ci
        build:
          commands:
            - npm run build
      artifacts:
        baseDirectory: frontend/build
        files:
          - '**/*'
      cache:
        paths:
          - frontend/node_modules/**/*
    appRoot: frontend
```

### **Method 2: Amplify CLI**
```bash
# Install Amplify CLI
npm install -g @aws-amplify/cli

# Run deployment script
./deploy-amplify.sh
```

### **Method 3: Manual Build**
```bash
# Build the application
./build-and-deploy.sh

# Upload build/ folder to Amplify Console
# Or sync to S3 bucket
```

---

## 🔧 **Configuration**

### **Environment Variables**

#### **Development (.env.development)**
```env
REACT_APP_API_URL=http://ncdhhs-pdf-qa-dev-alb-940310890.us-east-1.elb.amazonaws.com
REACT_APP_ENVIRONMENT=development
REACT_APP_VERSION=4.0.0
```

#### **Production (.env.production)**
```env
REACT_APP_API_URL=http://ncdhhs-pdf-qa-dev-alb-940310890.us-east-1.elb.amazonaws.com
REACT_APP_ENVIRONMENT=production
REACT_APP_VERSION=4.0.0
```

### **Backend API Endpoints**
- **Health Check**: `/health`
- **Knowledge Base Status**: `/knowledge-base-status`
- **Process PDFs**: `/process-and-upload-pdfs`
- **Ask Question**: `/ask-question`
- **Processing Status**: `/processing-status`

---

## 🧪 **Testing the Deployed Application**

### **Functional Tests**
1. **Knowledge Base Status**
   - Should show "ACTIVE" status
   - Display Knowledge Base ID: `EJRS8I2F6J`
   - Show Data Source ID: `PGYK8O2WDY`

2. **Q&A Functionality**
   - Ask: "What services does NCDHHS provide?"
   - Should return AI-generated response
   - Display source documents with confidence scores

3. **PDF Processing**
   - Enter a website URL with PDFs
   - Monitor real-time processing progress
   - Check successful upload to S3

### **Performance Tests**
- Page load time < 3 seconds
- API response time < 5 seconds
- Real-time updates every 2 seconds

---

## 🚀 **Production Deployment Checklist**

### **Pre-Deployment**
- [ ] Backend API is healthy and accessible
- [ ] Knowledge Base is ACTIVE
- [ ] Environment variables configured
- [ ] Build process tested locally

### **Deployment**
- [ ] Git repository connected to Amplify
- [ ] Build settings configured
- [ ] Environment variables set
- [ ] Custom domain configured (optional)

### **Post-Deployment**
- [ ] Application loads successfully
- [ ] All API endpoints working
- [ ] Knowledge Base integration functional
- [ ] Error handling working properly
- [ ] Mobile responsiveness verified

---

## 🔍 **Troubleshooting**

### **Common Issues**

#### **Build Failures**
```bash
# Clear npm cache
npm cache clean --force

# Delete node_modules and reinstall
rm -rf node_modules package-lock.json
npm install
```

#### **API Connection Issues**
- Verify backend ALB is running
- Check CORS configuration
- Validate environment variables

#### **Knowledge Base Errors**
- Confirm Knowledge Base ID is correct
- Check IAM permissions
- Verify Bedrock service availability

### **Debug Commands**
```bash
# Test backend API
curl http://ncdhhs-pdf-qa-dev-alb-940310890.us-east-1.elb.amazonaws.com/health

# Check build output
npm run build 2>&1 | tee build.log

# Verify environment variables
echo $REACT_APP_API_URL
```

---

## 📊 **Monitoring & Analytics**

### **AWS Amplify Monitoring**
- Build history and logs
- Performance metrics
- Error tracking
- User analytics

### **Backend Monitoring**
- CloudWatch logs and metrics
- ECS service health
- Bedrock usage statistics
- S3 storage metrics

---

## 🔒 **Security Considerations**

### **Frontend Security**
- Environment variables for sensitive config
- HTTPS enforcement
- Content Security Policy headers
- XSS protection

### **API Security**
- CORS properly configured
- Input validation
- Rate limiting
- Bedrock Guardrails active

---

## 📈 **Scaling & Performance**

### **Frontend Scaling**
- Amplify auto-scales globally
- CDN distribution included
- Caching optimizations

### **Backend Scaling**
- ECS auto-scaling configured
- Load balancer distribution
- Redis caching layer

---

## 🎯 **Next Steps**

1. **Deploy to Amplify** using preferred method
2. **Test all functionality** with production data
3. **Configure custom domain** (optional)
4. **Set up monitoring** and alerts
5. **Upload actual NCDHHS PDFs** for production use

---

**Deployment Status**: ✅ Ready for Production  
**Last Updated**: December 30, 2024  
**Version**: 4.0.0 (Bedrock Knowledge Base Integration)
