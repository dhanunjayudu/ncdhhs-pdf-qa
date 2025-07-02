# Local Development Guide

This guide explains how to develop the NC DHHS PDF Q&A application with the frontend running locally and the backend running on AWS.

## 🚀 Quick Start

### Option 1: Frontend Local + Backend AWS (Recommended)
```bash
./start-services.sh
```

This will:
- Run the React frontend locally on `http://localhost:3000`
- Connect to the AWS backend at `http://ncdhhs-pdf-qa-dev-alb-940310890.us-east-1.elb.amazonaws.com`
- Enable hot-reloading for frontend changes

### Option 2: Full Local Development
```bash
./start-services-local.sh
```

This will:
- Run both frontend and backend locally
- Frontend on `http://localhost:3000`
- Backend on `http://localhost:8000`
- Requires local Python environment setup

## 📁 Project Structure

```
├── frontend/                 # React frontend application
│   ├── .env                 # Default environment (AWS backend)
│   ├── .env.development     # Development environment (AWS backend)
│   ├── .env.local          # Local environment (created automatically)
│   └── src/                # Frontend source code
├── backend/                 # FastAPI backend application
├── start-services.sh       # Start frontend locally + AWS backend
├── start-services-local.sh # Start both frontend and backend locally
└── deploy-backend.sh       # Deploy backend changes to AWS
```

## 🔧 Development Workflow

### Frontend Development
1. Start the development environment:
   ```bash
   ./start-services.sh
   ```

2. Make changes to files in `frontend/src/`

3. Changes will automatically reload in your browser

4. The frontend will connect to the AWS backend automatically

### Backend Development
1. Make changes to files in `backend/`

2. Deploy changes to AWS:
   ```bash
   ./deploy-backend.sh
   ```

3. The script will:
   - Build a new Docker image
   - Push it to Amazon ECR
   - Update the ECS service
   - Wait for deployment to complete

4. Your local frontend will automatically use the updated backend

## 🌐 Environment Variables

The frontend uses different environment files based on the development mode:

### `.env` (Default)
- Used when no other environment file is present
- Points to AWS backend

### `.env.development`
- Used during `npm run dev`
- Points to AWS backend

### `.env.local` (Auto-generated)
- Created automatically by scripts
- Overrides other environment files
- Can point to local or AWS backend

### Available Variables
- `REACT_APP_API_URL`: Backend API URL
- `REACT_APP_TITLE`: Application title
- `REACT_APP_AWS_REGION`: AWS region
- `REACT_APP_ENVIRONMENT`: Environment name
- `REACT_APP_VERSION`: Application version

## 🔍 Troubleshooting

### Frontend won't start
```bash
cd frontend
npm install
npm run dev
```

### Backend connectivity issues
1. Check if AWS backend is running:
   ```bash
   curl http://ncdhhs-pdf-qa-dev-alb-940310890.us-east-1.elb.amazonaws.com/health
   ```

2. Check your internet connection

3. Verify the load balancer URL is correct

### CORS Issues
If you see CORS errors in the browser console:
1. The backend should already be configured for CORS
2. Try refreshing the page
3. Check browser developer tools for specific error messages

### ESLint Warnings
If you see ESLint warnings about React hooks dependencies:
1. These are warnings, not errors - the app will still work
2. The warnings help ensure proper React hook usage
3. You can ignore them for development or fix them by following the suggestions

### Deployment Issues
If `./deploy-backend.sh` fails:
1. Ensure AWS CLI is configured: `aws configure`
2. Ensure Docker is running: `docker info`
3. Check AWS permissions for ECR and ECS
4. Check the AWS console for detailed error messages

## 📝 Development Tips

### Hot Reloading
- Frontend changes reload automatically
- Backend changes require deployment to AWS
- Use `./start-services-local.sh` if you need backend hot reloading

### Debugging
- Frontend: Use browser developer tools
- Backend: Check CloudWatch logs in AWS console
- API testing: Use the API docs at `/docs` endpoint

### Performance
- Frontend development is fast (local)
- Backend deployment takes 2-3 minutes
- Consider batching backend changes

## 🔄 Switching Between Modes

### To use AWS backend (default):
```bash
./start-services.sh
```

### To use local backend:
```bash
./start-services-local.sh
```

### To deploy backend changes:
```bash
./deploy-backend.sh
```

## 🛠 Prerequisites

### Required Software
- Node.js (v16 or higher)
- Python 3.8+
- Docker
- AWS CLI

### AWS Configuration
```bash
aws configure
# Enter your AWS credentials and region
```

### Initial Setup
```bash
# Install frontend dependencies
cd frontend
npm install

# Install backend dependencies (for local development)
cd ../backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 🚨 Important Notes

1. **Environment Files**: Don't commit `.env.local` to git
2. **AWS Costs**: Be mindful of AWS usage when deploying frequently
3. **Security**: Never commit AWS credentials to git
4. **CORS**: The backend is configured to allow requests from localhost:3000
5. **Hot Reloading**: Only frontend has hot reloading in the recommended setup

## 📞 Support

If you encounter issues:
1. Check this guide first
2. Look at the console output for error messages
3. Check AWS CloudWatch logs for backend issues
4. Verify all prerequisites are installed and configured
