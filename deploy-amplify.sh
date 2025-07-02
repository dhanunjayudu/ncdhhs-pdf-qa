#!/bin/bash

# NCDHHS PDF Q&A System - AWS Amplify Deployment Script

set -e

echo "🚀 Deploying NCDHHS PDF Q&A System to AWS Amplify"
echo "=================================================="

# Check if AWS CLI is configured
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ AWS CLI not configured. Please run 'aws configure'"
    exit 1
fi

# Navigate to project root
cd "$(dirname "$0")"

# Build the frontend first
echo "🔨 Building frontend..."
cd frontend
npm ci
npm run build

if [ ! -d "build" ]; then
    echo "❌ Build failed - build directory not found"
    exit 1
fi

echo "✅ Frontend build completed!"
cd ..

# Check if Amplify CLI is installed
if ! command -v amplify &> /dev/null; then
    echo "📦 Installing Amplify CLI..."
    npm install -g @aws-amplify/cli
fi

# Create Amplify app using AWS CLI (more reliable than Amplify CLI)
APP_NAME="ncdhhs-pdf-qa-frontend"
echo "🔍 Checking if Amplify app exists..."

APP_ID=$(aws amplify list-apps --query "apps[?name=='$APP_NAME'].appId" --output text 2>/dev/null || echo "")

if [ -z "$APP_ID" ]; then
    echo "📱 Creating new Amplify app..."
    
    # Create the build spec content
    BUILD_SPEC=$(cat << 'EOL'
version: 1
applications:
  - frontend:
      phases:
        preBuild:
          commands:
            - cd frontend
            - echo "Installing dependencies..."
            - npm ci
            - echo "Setting environment variables..."
            - export DISABLE_ESLINT_PLUGIN=true
            - export ESLint_NO_DEV_ERRORS=true
            - export CI=false
        build:
          commands:
            - echo "Building React application..."
            - npm run build
            - echo "Build completed successfully"
      artifacts:
        baseDirectory: frontend/build
        files:
          - '**/*'
      cache:
        paths:
          - frontend/node_modules/**/*
    appRoot: frontend
EOL
)

    APP_ID=$(aws amplify create-app \
        --name "$APP_NAME" \
        --description "NCDHHS PDF Q&A System Frontend" \
        --platform "WEB" \
        --build-spec "$BUILD_SPEC" \
        --environment-variables REACT_APP_API_URL=http://ncdhhs-pdf-qa-dev-alb-940310890.us-east-1.elb.amazonaws.com,REACT_APP_ENVIRONMENT=production,REACT_APP_VERSION=4.0.0 \
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
    2>/dev/null || echo "ℹ️  Branch already exists"

# Get the app URL
APP_URL=$(aws amplify get-app --app-id "$APP_ID" --query 'app.defaultDomain' --output text)
FULL_URL="https://$BRANCH_NAME.$APP_URL"

echo ""
echo "✅ Deployment setup completed!"
echo "=================================================="
echo "📱 App ID: $APP_ID"
echo "🌐 URL: $FULL_URL"
echo ""
echo "🔗 To complete deployment:"
echo "1. Go to: https://console.aws.amazon.com/amplify/home#/$APP_ID"
echo "2. Connect your GitHub repository"
echo "3. Select the main branch"
echo "4. The build will start automatically"
echo ""
echo "Or deploy manually by uploading the build folder:"
echo "1. Zip the frontend/build folder"
echo "2. Upload via Amplify Console"
echo ""
echo "🎉 Setup completed successfully!"
