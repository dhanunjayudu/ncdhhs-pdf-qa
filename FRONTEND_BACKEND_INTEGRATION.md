# Frontend-Backend Integration Guide

This document outlines how the updated frontend components integrate with the current backend API endpoints.

## 🔄 **API Endpoint Mapping**

### **Current Backend Endpoints:**
```python
POST /extract-pdf-links      # Extract PDF links from website
POST /process-pdf-batch      # Process multiple PDFs in batch
POST /create-knowledge-base  # Create searchable knowledge base
POST /ask-question          # Q&A with Bedrock integration
GET  /documents             # List processed documents
GET  /health                # System health check
```

### **Frontend Component Integration:**

## 📄 **Enhanced PDF Processor**

### **Processing Flow:**
1. **Extract Links**: `POST /extract-pdf-links`
   ```javascript
   const response = await axios.post(`${API_URL}/extract-pdf-links`, {
     url: websiteUrl
   });
   ```

2. **Process PDFs**: `POST /process-pdf-batch`
   ```javascript
   const response = await axios.post(`${API_URL}/process-pdf-batch`, {
     pdf_urls: pdfLinks
   });
   ```

3. **Create Knowledge Base**: `POST /create-knowledge-base`
   ```javascript
   const response = await axios.post(`${API_URL}/create-knowledge-base`, {
     documents: successfulDocs
   });
   ```

### **Key Changes from Previous Version:**
- ❌ **Removed**: WebSocket connections (not implemented in current backend)
- ❌ **Removed**: Async job tracking with job IDs
- ✅ **Added**: Sequential processing with progress tracking
- ✅ **Added**: Automatic knowledge base creation
- ✅ **Added**: Better error handling and status updates

## 💬 **Enhanced Chat Interface**

### **Q&A Flow:**
1. **Ask Question**: `POST /ask-question`
   ```javascript
   const response = await axios.post(`${API_URL}/ask-question`, {
     question: userQuestion,
     use_guardrails: true,
     max_results: 5
   });
   ```

### **Key Changes from Previous Version:**
- ❌ **Removed**: Separate search and answer endpoints
- ❌ **Removed**: Advanced search mode selection
- ✅ **Added**: Direct question answering with current backend
- ✅ **Added**: Backend status monitoring
- ✅ **Added**: Simplified guardrails toggle
- ✅ **Added**: Better error handling for model availability

## 🏥 **System Health Integration**

### **Health Check:**
```javascript
const response = await fetch(`${API_URL}/health`);
const status = await response.json();
```

### **Status Indicators:**
- **Backend API**: Connection status
- **OpenSearch**: Search capability
- **S3 Storage**: Document storage
- **Bedrock Models**: AI model availability

## 🔧 **Environment Variables**

### **Frontend (.env):**
```bash
VITE_API_URL=http://your-backend-url
VITE_APP_TITLE=NCDHHS PDF Q&A Assistant
VITE_AWS_REGION=us-east-1
```

### **Backend (from Terraform):**
```bash
BEDROCK_GUARDRAIL_ID=your-guardrail-id
BEDROCK_GUARDRAIL_VERSION=1
S3_KNOWLEDGE_BASE_BUCKET=your-s3-bucket
BEDROCK_PRIMARY_MODEL=amazon.nova-pro-v1:0
BEDROCK_FAST_MODEL=amazon.nova-lite-v1:0
BEDROCK_EMBEDDING_MODEL=amazon.titan-embed-text-v2:0
```

## 📊 **Data Flow**

### **PDF Processing:**
```
User Input (URL) 
  ↓
Extract PDF Links 
  ↓
Process PDFs in Batch 
  ↓
Create Knowledge Base 
  ↓
Update Frontend State
```

### **Q&A Process:**
```
User Question 
  ↓
Backend Search & AI Processing 
  ↓
Bedrock Model Response 
  ↓
Display Answer with Sources
```

## 🔄 **State Management**

### **Document State:**
```javascript
const [documents, setDocuments] = useState([]);

// Add new documents (append, don't replace)
const handleDocumentsProcessed = (processedDocs) => {
  setDocuments(prev => [...prev, ...processedDocs]);
};
```

### **Processing State:**
```javascript
const [isProcessing, setIsProcessing] = useState(false);
const [processingStatus, setProcessingStatus] = useState('');
const [progress, setProgress] = useState(null);
```

## 🚨 **Error Handling**

### **Common Error Scenarios:**

1. **Backend Unavailable:**
   ```javascript
   if (error.code === 'ECONNREFUSED') {
     setSystemStatus({ status: 'error', message: 'Backend unavailable' });
   }
   ```

2. **Model Not Enabled:**
   ```javascript
   if (error.response?.status === 503) {
     errorContent = 'AI service unavailable. Check Bedrock model access.';
   }
   ```

3. **No PDFs Found:**
   ```javascript
   if (pdfCount === 0) {
     throw new Error('No PDF files found on the website');
   }
   ```

## 🎯 **User Experience Flow**

### **Happy Path:**
1. User enters website URL
2. System extracts PDF links
3. PDFs are processed in batch
4. Knowledge base is created automatically
5. User can ask questions immediately
6. AI provides answers with source attribution

### **Error Recovery:**
1. Clear error messages displayed
2. System status indicators show issues
3. Graceful degradation when services unavailable
4. Retry mechanisms for transient failures

## 🔧 **Development & Testing**

### **Local Development:**
```bash
# Backend
cd backend/
python -m uvicorn main:app --reload --port 8000

# Frontend
cd frontend/
npm run dev
```

### **Testing Integration:**
1. **Health Check**: Verify `/health` endpoint
2. **PDF Processing**: Test with sample website
3. **Q&A**: Ask questions about processed documents
4. **Error Handling**: Test with invalid URLs/questions

## 📈 **Performance Considerations**

### **Frontend Optimizations:**
- Debounced input for search
- Lazy loading of components
- Efficient state updates
- Error boundary implementation

### **Backend Integration:**
- Timeout handling for long requests
- Progress feedback during processing
- Efficient document state management
- Proper cleanup on component unmount

## 🔄 **Migration Notes**

### **From Previous Version:**
- **WebSocket features** → **HTTP polling/status updates**
- **Complex async job management** → **Simplified batch processing**
- **Multiple search endpoints** → **Single Q&A endpoint**
- **Advanced search modes** → **Simplified question answering**

### **Benefits of Current Approach:**
- ✅ Simpler architecture
- ✅ More reliable (no WebSocket dependencies)
- ✅ Better error handling
- ✅ Easier to deploy and maintain
- ✅ Works with current backend capabilities

---

**The frontend is now fully aligned with the current backend implementation and ready for deployment!** 🚀
