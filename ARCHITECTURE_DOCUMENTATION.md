# NCDHHS PDF Q&A System - Architecture Documentation

## 📋 Overview

The NCDHHS PDF Q&A System is a comprehensive cloud-native application built on AWS that enables North Carolina Department of Health and Human Services staff to upload PDF documents and ask natural language questions about their content. The system uses advanced AI capabilities through Amazon Bedrock to provide intelligent, contextual answers with source citations.

## 🏗️ Architecture Diagrams

### 1. Complete System Architecture (`architecture-diagram.png`)
- **Purpose**: Comprehensive overview of all system components and their relationships
- **Shows**: User layer, frontend (Amplify), backend (ECS), AWS services, data flow, and configuration details
- **Use Case**: Understanding the complete system at a high level

### 2. Data Flow Architecture (`data-flow-diagram.png`)
- **Purpose**: Illustrates how data moves through the system during upload and query operations
- **Shows**: Step-by-step data processing from user action to final response
- **Use Case**: Understanding the processing pipeline and data transformations

### 3. Component Interaction (`component-diagram.png`)
- **Purpose**: Detailed view of software components and their interactions
- **Shows**: Frontend components, backend APIs, business logic, AWS clients, and service integrations
- **Use Case**: Development, debugging, and system maintenance

### 4. Network & Security (`network-security-diagram.png`)
- **Purpose**: Network topology, security groups, IAM roles, and data protection measures
- **Shows**: VPC structure, subnets, security groups, encryption, and access controls
- **Use Case**: Security audits, compliance, and network troubleshooting

## 🎯 System Components

### Frontend Layer (AWS Amplify)
```
Technology: React.js (Create React App)
Hosting: AWS Amplify with CloudFront CDN
Domain: Custom domain with SSL certificate
Features:
├── PDF Upload Interface
├── Q&A Chat Interface  
├── Status Dashboard
├── Admin Controls
└── Real-time Progress Tracking
```

### Backend Layer (Amazon ECS Fargate)
```
Technology: FastAPI (Python)
Container: Docker on ECS Fargate
Load Balancer: Application Load Balancer
Auto Scaling: Based on CPU/Memory utilization
Features:
├── RESTful API Endpoints
├── PDF Processing Pipeline
├── Knowledge Base Integration
├── Status Management
└── Health Monitoring
```

### Data Storage & AI Services
```
Document Storage: Amazon S3
Vector Database: OpenSearch Serverless
Knowledge Base: Amazon Bedrock Knowledge Base
AI Models:
├── amazon.nova-pro-v1:0 (Question Answering)
├── amazon.titan-embed-text-v2:0 (Embeddings)
└── Guardrails for content filtering
```

## 🔄 Data Processing Pipeline

### PDF Upload & Ingestion Flow
```
1. User Input → Website URL with PDF links
2. Backend Processing → Web scraping and PDF download
3. S3 Storage → Secure document storage with versioning
4. Knowledge Base Sync → Automatic ingestion job trigger
5. Text Extraction → PDF content parsing and chunking
6. Embedding Generation → Vector representations using Titan
7. Vector Storage → OpenSearch Serverless indexing
8. Status Update → Real-time progress tracking
```

### Question & Answer Flow
```
1. User Query → Natural language question input
2. Query Processing → Question analysis and preparation
3. Semantic Search → Vector similarity search in OpenSearch
4. Context Retrieval → Relevant document chunks extraction
5. LLM Processing → Answer generation using Nova Pro
6. Response Formatting → Answer with source citations
7. UI Display → Formatted response with confidence scores
```

## 🔐 Security Architecture

### Network Security
- **VPC Isolation**: Private subnets for compute resources
- **Security Groups**: Restrictive inbound/outbound rules
- **SSL/TLS**: End-to-end encryption for all communications
- **NAT Gateways**: Secure outbound internet access for containers

### Data Protection
- **Encryption at Rest**: S3, OpenSearch, and CloudWatch logs
- **Encryption in Transit**: HTTPS/TLS for all API communications
- **Access Control**: IAM roles with least privilege principles
- **Audit Logging**: CloudTrail and service-specific logs

### Identity & Access Management
```
ECS Task Role:
├── S3 bucket read/write permissions
├── Bedrock service access
├── CloudWatch logs write access
└── Parameter Store read access

Knowledge Base Role:
├── S3 bucket read permissions
├── OpenSearch collection write access
├── Bedrock model invocation
└── Cross-service assume role permissions
```

## 📊 AWS Services Configuration

### Core Services
| Service | Resource ID | Purpose |
|---------|-------------|---------|
| **S3 Bucket** | `ncdhhs-pdf-qa-dev-bedrock-kb-f04187f9` | Document storage |
| **Knowledge Base** | `EJRS8I2F6J` | AI-powered document indexing |
| **Data Source** | `PGYK8O2WDY` | S3 integration for KB |
| **OpenSearch Collection** | `14dzr3m6d071boqiytt6` | Vector search engine |
| **ECS Cluster** | `ncdhhs-pdf-qa-dev-cluster` | Container orchestration |
| **ECS Service** | `ncdhhs-pdf-qa-dev-service` | Application service |
| **Load Balancer** | `ncdhhs-pdf-qa-dev-alb` | Traffic distribution |

### Compute Configuration
```
ECS Fargate Task:
├── CPU: 1 vCPU (1024 units)
├── Memory: 2 GB (2048 MB)
├── Network Mode: awsvpc
├── Platform Version: LATEST
└── Desired Count: 1 (auto-scaling enabled)

Container Configuration:
├── Image: FastAPI application
├── Port: 8000 (HTTP)
├── Health Check: GET /health
├── Environment Variables: AWS region, service IDs
└── Logging: CloudWatch Logs
```

### AI/ML Configuration
```
Bedrock Knowledge Base:
├── Type: VECTOR
├── Embedding Model: amazon.titan-embed-text-v2:0
├── Dimensions: 1024
├── Data Type: FLOAT32
└── Index: bedrock-kb-faiss-index

OpenSearch Serverless:
├── Collection Type: VECTORSEARCH
├── Vector Field: bedrock-knowledge-base-default-vector
├── Text Field: AMAZON_BEDROCK_TEXT_CHUNK
├── Metadata Field: AMAZON_BEDROCK_METADATA
└── Encryption: AWS managed keys
```

## 🚀 Deployment Architecture

### Frontend Deployment (AWS Amplify)
```
Build Process:
├── Source: React application
├── Build Command: npm run build
├── Output Directory: build/
├── Node Version: 18.x
└── Environment Variables: API_URL, VERSION

Distribution:
├── CloudFront CDN: Global edge locations
├── SSL Certificate: AWS Certificate Manager
├── Custom Domain: Optional configuration
├── Caching: Static assets cached at edge
└── Compression: Gzip/Brotli enabled
```

### Backend Deployment (ECS)
```
Container Registry:
├── Amazon ECR: ncdhhs-pdf-qa-dev-backend
├── Image Scanning: Vulnerability detection
├── Lifecycle Policy: Automated cleanup
└── Cross-region Replication: Optional

Deployment Strategy:
├── Rolling Updates: Zero-downtime deployments
├── Health Checks: Application and load balancer
├── Auto Rollback: On deployment failures
├── Blue/Green: Optional advanced deployment
└── Monitoring: CloudWatch metrics and alarms
```

## 📈 Monitoring & Observability

### Application Monitoring
```
CloudWatch Metrics:
├── ECS Service: CPU, Memory, Task count
├── Load Balancer: Request count, latency, errors
├── S3: Request metrics, storage utilization
├── Bedrock: API calls, latency, errors
└── Custom Metrics: Processing status, queue depth

CloudWatch Logs:
├── Application Logs: FastAPI request/response logs
├── Container Logs: Docker stdout/stderr
├── Load Balancer Logs: Access logs with request details
└── VPC Flow Logs: Network traffic analysis
```

### Alerting Strategy
```
Critical Alerts:
├── Service Health: ECS task failures
├── High Latency: API response times > 5s
├── Error Rates: HTTP 5xx errors > 5%
├── Resource Utilization: CPU/Memory > 80%
└── Knowledge Base: Ingestion job failures

Notification Channels:
├── Email: Operations team notifications
├── Slack: Real-time alerts (optional)
├── SNS: Programmatic alert handling
└── Dashboard: CloudWatch dashboard views
```

## 🔧 Configuration Management

### Environment Variables
```
Backend Configuration:
├── AWS_REGION=us-east-1
├── S3_KNOWLEDGE_BASE_BUCKET=ncdhhs-pdf-qa-dev-bedrock-kb-f04187f9
├── BEDROCK_KNOWLEDGE_BASE_ID=EJRS8I2F6J
├── BEDROCK_DATA_SOURCE_ID=PGYK8O2WDY
├── BEDROCK_PRIMARY_MODEL=amazon.nova-pro-v1:0
├── BEDROCK_GUARDRAIL_ID=d6wcptfamw16
└── OPENSEARCH_COLLECTION_ARN=arn:aws:aoss:us-east-1:942713336312:collection/14dzr3m6d071boqiytt6

Frontend Configuration:
├── REACT_APP_API_URL=http://ncdhhs-pdf-qa-dev-alb-940310890.us-east-1.elb.amazonaws.com
├── REACT_APP_ENVIRONMENT=production
└── REACT_APP_VERSION=4.0.0
```

### Build Specifications
```yaml
# amplify.yml - Frontend Build
version: 1
applications:
  - frontend:
      phases:
        preBuild:
          commands:
            - cd frontend
            - npm ci
            - export DISABLE_ESLINT_PLUGIN=true
            - export CI=false
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

## 🎯 API Endpoints Reference

### Core Endpoints
| Method | Endpoint | Purpose | Request | Response |
|--------|----------|---------|---------|----------|
| `GET` | `/health` | Health check | None | Service status |
| `GET` | `/` | API information | None | Version, architecture |
| `POST` | `/process-and-upload-pdfs` | PDF processing | Website URL | Processing status |
| `POST` | `/ask-question` | Q&A queries | Question text | Answer + sources |
| `GET` | `/detailed-status` | System status | None | Complete status |
| `GET` | `/processing-status` | Processing status | None | Current progress |
| `POST` | `/trigger-sync` | Manual sync | None | Job ID |
| `POST` | `/clear-processing-status` | Clear status | None | Success message |

### Request/Response Examples
```json
// POST /ask-question
{
  "question": "What are the cash management policies?",
  "max_results": 5
}

// Response
{
  "answer": "The cash management policies for NCDHHS...",
  "sources": [
    {
      "uri": "s3://bucket/document.pdf",
      "score": 0.85,
      "excerpt": "Policy excerpt..."
    }
  ],
  "confidence": 0.85,
  "processing_time": 2.3
}
```

## 🔄 Scaling & Performance

### Horizontal Scaling
```
ECS Service Auto Scaling:
├── Target Tracking: CPU utilization 70%
├── Min Capacity: 1 task
├── Max Capacity: 10 tasks
├── Scale Out: +1 task when CPU > 70% for 2 minutes
└── Scale In: -1 task when CPU < 50% for 5 minutes

Load Balancer:
├── Cross-zone Load Balancing: Enabled
├── Connection Draining: 300 seconds
├── Health Check: /health endpoint
└── Sticky Sessions: Disabled (stateless)
```

### Performance Optimization
```
Frontend Optimization:
├── Code Splitting: React lazy loading
├── Asset Optimization: Minification, compression
├── CDN Caching: Static assets cached globally
├── Bundle Analysis: Webpack bundle analyzer
└── Progressive Loading: Skeleton screens

Backend Optimization:
├── Connection Pooling: Database connections
├── Caching: In-memory response caching
├── Async Processing: Background tasks
├── Request Batching: Multiple operations
└── Resource Limits: CPU/memory constraints
```

## 🛠️ Development & Maintenance

### Local Development
```bash
# Frontend Development
cd frontend
npm install
npm run start:local  # Uses localhost:8000 backend

# Backend Development
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Full Stack Development
./start-services-local.sh  # Starts both frontend and backend
```

### Deployment Process
```bash
# Backend Deployment
./deploy-backend.sh  # Builds and deploys to ECS

# Frontend Deployment
./deploy-amplify.sh  # Deploys to AWS Amplify

# Full Deployment
./build-and-deploy.sh  # Complete deployment pipeline
```

### Monitoring Commands
```bash
# View Logs
./monitor-logs.sh  # Interactive log monitoring

# Check Status
curl https://api-url/health  # Health check
curl https://api-url/detailed-status  # Full status

# Manual Operations
curl -X POST https://api-url/trigger-sync  # Manual sync
curl -X POST https://api-url/clear-processing-status  # Clear status
```

## 📚 Additional Resources

### Documentation Files
- `DEPLOYMENT_GUIDE.md` - Step-by-step deployment instructions
- `LOCAL_DEVELOPMENT.md` - Local development setup
- `FRONTEND_BACKEND_INTEGRATION.md` - API integration details
- `SIMPLIFIED_ARCHITECTURE.md` - High-level architecture overview

### Diagram Files
- `architecture-diagram.dot` - Graphviz source for main architecture
- `data-flow-diagram.dot` - Graphviz source for data flow
- `component-diagram.dot` - Graphviz source for components
- `network-security-diagram.dot` - Graphviz source for network/security

### Generated Diagrams
- `architecture-diagram.png` - Complete system overview
- `data-flow-diagram.png` - Data processing flow
- `component-diagram.png` - Component interactions
- `network-security-diagram.png` - Network and security architecture

---

## 🎉 Summary

This architecture provides a robust, scalable, and secure foundation for the NCDHHS PDF Q&A system. The design emphasizes:

- **Scalability**: Auto-scaling compute resources and managed services
- **Security**: End-to-end encryption and least-privilege access
- **Reliability**: Multi-AZ deployment and health monitoring
- **Performance**: CDN distribution and optimized AI processing
- **Maintainability**: Clear separation of concerns and comprehensive monitoring

The system successfully combines modern web technologies with advanced AI capabilities to deliver an intuitive and powerful document query experience for NCDHHS staff.
