# AWS Amplify Deployment Troubleshooting

## 🚨 Current Issue
- **Domain**: https://main.diwv3sayephw0.amplifyapp.com
- **Status**: Deployment Failed
- **Root Cause**: Missing Dependencies

## 🔍 Identified Problems

### 1. Missing Dependencies in package.json
Your components use these packages that are NOT in package.json:
```javascript
❌ lucide-react  - Used for icons (Send, MessageCircle, User, Bot, etc.)
❌ axios         - Used for API calls
```

### 2. Current package.json Dependencies
```json
{
  "dependencies": {
    "react": "^18.2.0",           ✅ Present
    "react-dom": "^18.2.0",       ✅ Present  
    "react-scripts": "5.0.1",     ✅ Present
    "web-vitals": "^2.1.4"        ✅ Present
  }
}
```

### 3. Required Dependencies (Missing)
```json
{
  "dependencies": {
    "axios": "^1.6.0",           ❌ MISSING - API calls
    "lucide-react": "^0.263.1"   ❌ MISSING - Icons
  }
}
```

## 🔧 Step-by-Step Fix

### Step 1: Add Missing Dependencies
```bash
cd frontend
npm install axios lucide-react
```

### Step 2: Verify package.json
After installation, package.json should include:
```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0", 
    "react-scripts": "5.0.1",
    "web-vitals": "^2.1.4",
    "axios": "^1.6.0",
    "lucide-react": "^0.263.1"
  }
}
```

### Step 3: Test Build Locally
```bash
cd frontend
npm run build
```

### Step 4: Update Amplify Build Configuration
Ensure amplify.yml has proper error handling:
```yaml
version: 1
applications:
  - frontend:
      phases:
        preBuild:
          commands:
            - cd frontend
            - echo "Node version:"
            - node --version
            - echo "NPM version:"
            - npm --version
            - echo "Installing dependencies..."
            - npm ci
            - echo "Dependencies installed successfully"
            - export DISABLE_ESLINT_PLUGIN=true
            - export CI=false
        build:
          commands:
            - echo "Building React application..."
            - npm run build
            - echo "Build completed successfully"
            - echo "Verifying build output:"
            - ls -la build/
            - test -f build/index.html || (echo "❌ index.html missing" && exit 1)
            - test -d build/static || (echo "❌ static directory missing" && exit 1)
        postBuild:
          commands:
            - echo "✅ Build verification passed"
      artifacts:
        baseDirectory: frontend/build
        files:
          - '**/*'
      cache:
        paths:
          - frontend/node_modules/**/*
    appRoot: frontend
```

### Step 5: Set Environment Variables in Amplify Console
```
REACT_APP_API_URL = http://ncdhhs-pdf-qa-dev-alb-940310890.us-east-1.elb.amazonaws.com
REACT_APP_ENVIRONMENT = production
REACT_APP_VERSION = 4.0.0
CI = false
DISABLE_ESLINT_PLUGIN = true
```

## 🔍 Common Amplify Build Errors

### Error 1: "Module not found: Can't resolve 'lucide-react'"
**Cause**: Missing lucide-react dependency
**Fix**: Add to package.json dependencies

### Error 2: "Module not found: Can't resolve 'axios'"
**Cause**: Missing axios dependency  
**Fix**: Add to package.json dependencies

### Error 3: "npm ERR! peer dep missing"
**Cause**: Peer dependency conflicts
**Fix**: Use npm ci instead of npm install

### Error 4: "Build failed with exit code 1"
**Cause**: ESLint errors or build failures
**Fix**: Set CI=false and DISABLE_ESLINT_PLUGIN=true

### Error 5: "No artifacts found"
**Cause**: Wrong baseDirectory or build output location
**Fix**: Ensure baseDirectory points to frontend/build

## 🧪 Testing Strategy

### Local Testing
```bash
# Test the exact build process Amplify will use
cd frontend
rm -rf node_modules package-lock.json
npm ci
npm run build
ls -la build/
```

### Build Verification
```bash
# Verify all required files exist
test -f build/index.html && echo "✅ index.html found"
test -d build/static && echo "✅ static directory found"
test -f build/static/js/*.js && echo "✅ JavaScript files found"
test -f build/static/css/*.css && echo "✅ CSS files found"
```

## 🚀 Deployment Options

### Option 1: Fix Current App
1. Add missing dependencies to package.json
2. Commit and push changes
3. Amplify will auto-deploy

### Option 2: Manual Upload (Quick Fix)
1. Fix dependencies locally
2. Build locally: `npm run build`
3. Upload build folder to Amplify Console

### Option 3: Create New App
1. Fix all issues locally
2. Create fresh Amplify app
3. Upload working build

## 📋 Checklist Before Deployment

- [ ] All dependencies in package.json
- [ ] Local build works: `npm run build`
- [ ] Environment variables set in Amplify
- [ ] amplify.yml configuration correct
- [ ] No ESLint errors (or ESLint disabled)
- [ ] Build artifacts in correct location

## 🔧 Quick Fix Commands

```bash
# Navigate to frontend
cd /Users/dhanunjayudusurisetty/ncdhhs-pdf-qa/frontend

# Add missing dependencies
npm install axios lucide-react

# Test build
npm run build

# Verify build output
ls -la build/

# Create deployment package
zip -r ../ncdhhs-frontend-fixed.zip build/
```

## 📞 Next Steps

1. **Add missing dependencies** (axios, lucide-react)
2. **Test build locally** to ensure it works
3. **Commit changes** to trigger auto-deployment
4. **Check Amplify Console logs** for specific error messages
5. **Set environment variables** in Amplify Console

The main issue is definitely the missing dependencies. Once those are added, the deployment should succeed!
