# AWS Amplify Deployment Troubleshooting Guide

## 🚨 Current Issue
- URL: https://staging.duisk83gae5d8.amplifyapp.com/
- Error: 404 - Failed to load resource

## 🔧 Step-by-Step Fix

### 1. Check Amplify Console Build Logs
1. Go to AWS Amplify Console: https://console.aws.amazon.com/amplify/
2. Click on your app
3. Go to "Build settings" tab
4. Check the build logs for errors

### 2. Update Build Settings in Amplify Console
Replace the build specification with:

```yaml
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
            - ls -la build/
        postBuild:
          commands:
            - echo "Build verification..."
            - test -f build/index.html && echo "✅ index.html found" || echo "❌ index.html missing"
      artifacts:
        baseDirectory: frontend/build
        files:
          - '**/*'
      cache:
        paths:
          - frontend/node_modules/**/*
    appRoot: frontend
```

### 3. Set Environment Variables in Amplify
In Amplify Console → Environment variables, add:
- `REACT_APP_API_URL` = `http://ncdhhs-pdf-qa-dev-alb-940310890.us-east-1.elb.amazonaws.com`
- `REACT_APP_ENVIRONMENT` = `production`
- `REACT_APP_VERSION` = `4.0.0`
- `CI` = `false`
- `DISABLE_ESLINT_PLUGIN` = `true`

### 4. Check App Root Setting
- In Amplify Console → App settings → General
- Make sure "App root" is set to: `frontend`

### 5. Manual Upload Option (If Git deployment fails)
1. Go to Amplify Console
2. Click "Deploy without Git provider"
3. Upload: `ncdhhs-frontend-build-v2.zip`
4. Set environment name: `production`

### 6. Verify Redirects and Rewrites
In Amplify Console → Rewrites and redirects, add:
```
Source: </^[^.]+$|\.(?!(css|gif|ico|jpg|js|png|txt|svg|woff|ttf|map|json)$)([^.]+$)/>
Target: /index.html
Type: 200 (Rewrite)
```

### 7. Common Issues and Solutions

#### Issue: Build fails with "Module not found"
Solution: Check package.json dependencies and run `npm install`

#### Issue: Environment variables not working
Solution: Restart the app after adding environment variables

#### Issue: 404 on refresh
Solution: Add the redirect rule from step 6

#### Issue: Static files not loading
Solution: Check if baseDirectory is set to `frontend/build`

## 🧪 Test Your Deployment

After fixing, test these URLs:
- https://staging.duisk83gae5d8.amplifyapp.com/ (should show the app)
- https://staging.duisk83gae5d8.amplifyapp.com/static/js/main.*.js (should load JS)
- https://staging.duisk83gae5d8.amplifyapp.com/static/css/main.*.css (should load CSS)

## 🔍 Debug Commands

If you have AWS CLI access:
```bash
# Check app details
aws amplify get-app --app-id YOUR_APP_ID

# Check branch details  
aws amplify get-branch --app-id YOUR_APP_ID --branch-name staging

# List deployments
aws amplify list-jobs --app-id YOUR_APP_ID --branch-name staging
```
