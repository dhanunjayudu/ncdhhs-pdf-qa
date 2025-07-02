#!/bin/bash

# Manual Frontend Deployment to AWS Amplify
set -e

echo "🚀 Deploying NCDHHS PDF Q&A Frontend to AWS Amplify"
echo "=================================================="

# Check if AWS CLI is configured
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ AWS CLI not configured. Please run 'aws configure'"
    exit 1
fi

# Navigate to frontend directory
cd frontend

# Build the application
echo "🔨 Building React application..."
npm run build

# Check if build was successful
if [ ! -d "build" ]; then
    echo "❌ Build failed - build directory not found"
    exit 1
fi

echo "✅ Build completed successfully!"

# Create Amplify app (if it doesn't exist)
APP_NAME="ncdhhs-pdf-qa-frontend"
echo "🔍 Checking if Amplify app exists..."

APP_ID=$(aws amplify list-apps --query "apps[?name=='$APP_NAME'].appId" --output text 2>/dev/null || echo "")

if [ -z "$APP_ID" ]; then
    echo "📱 Creating new Amplify app..."
    APP_ID=$(aws amplify create-app \
        --name "$APP_NAME" \
        --description "NCDHHS PDF Q&A System Frontend" \
        --repository "https://github.com/your-username/ncdhhs-pdf-qa" \
        --platform "WEB" \
        --environment-variables REACT_APP_API_URL=http://ncdhhs-pdf-qa-dev-alb-940310890.us-east-1.elb.amazonaws.com,REACT_APP_ENVIRONMENT=production \
        --query 'app.appId' \
        --output text)
    echo "✅ Created Amplify app with ID: $APP_ID"
else
    echo "✅ Found existing Amplify app with ID: $APP_ID"
fi

# Create or update branch
BRANCH_NAME="main"
echo "🌿 Setting up branch: $BRANCH_NAME"

aws amplify create-branch \
    --app-id "$APP_ID" \
    --branch-name "$BRANCH_NAME" \
    --description "Main production branch" \
    --enable-auto-build \
    2>/dev/null || echo "Branch already exists"

# Start deployment
echo "🚀 Starting deployment..."
JOB_ID=$(aws amplify start-job \
    --app-id "$APP_ID" \
    --branch-name "$BRANCH_NAME" \
    --job-type RELEASE \
    --query 'jobSummary.jobId' \
    --output text)

echo "✅ Deployment started with Job ID: $JOB_ID"

# Get the app URL
APP_URL=$(aws amplify get-app --app-id "$APP_ID" --query 'app.defaultDomain' --output text)
echo "🌐 Your app will be available at: https://$BRANCH_NAME.$APP_URL"

echo ""
echo "🎉 Deployment initiated successfully!"
echo "=================================================="
echo "📱 App ID: $APP_ID"
echo "🆔 Job ID: $JOB_ID"
echo "🌐 URL: https://$BRANCH_NAME.$APP_URL"
echo ""
echo "⏳ Deployment may take 2-5 minutes to complete."
echo "📊 Monitor progress at: https://console.aws.amazon.com/amplify/home#/$APP_ID"

