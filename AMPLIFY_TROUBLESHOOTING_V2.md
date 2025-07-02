# 🚨 AWS Amplify Deployment Troubleshooting - Round 2

## Current Status
- **Domain**: https://main.diwv3sayephw0.amplifyapp.com
- **Git Commit**: ✅ Successfully pushed with dependencies
- **Issue**: Deployment still failing after adding dependencies

## 🔍 Potential Issues & Solutions

### Issue 1: Amplify Build Configuration Problems

#### Problem: Wrong Node.js Version
Amplify might be using an incompatible Node.js version.

#### Solution: Force Node.js Version
Update `amplify.yml`:
```yaml
version: 1
applications:
  - frontend:
      phases:
        preBuild:
          commands:
            - cd frontend
            - echo "=== Setting Node.js Version ==="
            - nvm install 18
            - nvm use 18
            - node --version
            - npm --version
            - echo "=== Installing Dependencies ==="
            - npm ci
            - echo "=== Setting Build Environment ==="
            - export DISABLE_ESLINT_PLUGIN=true
            - export CI=false
        build:
          commands:
            - echo "=== Building Application ==="
            - npm run build
            - echo "=== Verifying Build ==="
            - ls -la build/
            - test -f build/index.html || exit 1
      artifacts:
        baseDirectory: frontend/build
        files:
          - '**/*'
      cache:
        paths:
          - frontend/node_modules/**/*
    appRoot: frontend
```

### Issue 2: Environment Variables Not Set

#### Problem: Missing Environment Variables in Amplify Console
Even with Git deployment, environment variables must be set in Amplify Console.

#### Solution: Set Environment Variables
Go to Amplify Console → Your App → Environment Variables:
```
REACT_APP_API_URL = http://ncdhhs-pdf-qa-dev-alb-940310890.us-east-1.elb.amazonaws.com
REACT_APP_ENVIRONMENT = production
REACT_APP_VERSION = 4.0.0
CI = false
DISABLE_ESLINT_PLUGIN = true
NODE_OPTIONS = --max-old-space-size=4096
```

### Issue 3: ESLint/Build Errors

#### Problem: ESLint or TypeScript errors causing build failure

#### Solution: Create .env file in frontend
```bash
# Create frontend/.env
DISABLE_ESLINT_PLUGIN=true
ESLINT_NO_DEV_ERRORS=true
CI=false
```

### Issue 4: Package-lock.json Conflicts

#### Problem: npm ci failing due to package-lock.json issues

#### Solution: Regenerate package-lock.json
```bash
cd frontend
rm package-lock.json
npm install
git add package-lock.json
git commit -m "Fix: Regenerate package-lock.json"
git push
```

### Issue 5: Build Specification Issues

#### Problem: Amplify not using the correct amplify.yml

#### Solution: Set Build Settings in Console
1. Go to Amplify Console → Your App → Build Settings
2. Click "Edit"
3. Replace with this build specification:

```yaml
version: 1
applications:
  - frontend:
      phases:
        preBuild:
          commands:
            - cd frontend
            - nvm use 18
            - npm ci
            - export DISABLE_ESLINT_PLUGIN=true
            - export CI=false
        build:
          commands:
            - npm run build
        postBuild:
          commands:
            - echo "Build completed"
      artifacts:
        baseDirectory: frontend/build
        files:
          - '**/*'
      cache:
        paths:
          - frontend/node_modules/**/*
    appRoot: frontend
```

## 🚀 IMMEDIATE ACTION PLAN

### Step 1: Quick Manual Fix (Recommended)
Since Git deployment is failing, let's use manual upload:

1. **Go to Amplify Console**: https://console.aws.amazon.com/amplify/
2. **Find your app** (main.diwv3sayephw0.amplifyapp.com)
3. **Click "Actions" → "Deploy updates"**
4. **Upload**: `ncdhhs-frontend-FIXED.zip` (we created this earlier)
5. **Wait for deployment**

### Step 2: Set Environment Variables
In Amplify Console → Environment Variables, add:
```
REACT_APP_API_URL = http://ncdhhs-pdf-qa-dev-alb-940310890.us-east-1.elb.amazonaws.com
REACT_APP_ENVIRONMENT = production
CI = false
DISABLE_ESLINT_PLUGIN = true
```

### Step 3: Fix Git Deployment for Future
After manual upload works, fix Git deployment:

1. **Create frontend/.env**:
```bash
cd frontend
cat > .env << 'EOF'
DISABLE_ESLINT_PLUGIN=true
ESLINT_NO_DEV_ERRORS=true
CI=false
EOF
```

2. **Regenerate package-lock.json**:
```bash
rm package-lock.json
npm install
```

3. **Commit changes**:
```bash
git add .
git commit -m "Fix: Add .env and regenerate package-lock.json"
git push
```

### Step 4: Alternative - Create New Amplify App
If the current app is corrupted:

1. **Create new Amplify app**
2. **Connect to GitHub repository**
3. **Use the fixed build settings**
4. **Set environment variables**

## 🔧 Debug Commands

### Check Amplify Build Logs
1. Go to Amplify Console
2. Click on your app
3. Go to "Build history"
4. Click on the failed build
5. Check the logs for specific errors

### Common Error Messages & Fixes

#### "Module not found: Can't resolve 'axios'"
- **Cause**: Dependencies not installed
- **Fix**: Ensure package.json has axios and npm ci runs successfully

#### "npm ERR! peer dep missing"
- **Cause**: Peer dependency issues
- **Fix**: Delete package-lock.json and regenerate

#### "Build failed with exit code 1"
- **Cause**: ESLint errors or build failures
- **Fix**: Set CI=false and DISABLE_ESLINT_PLUGIN=true

#### "No artifacts found"
- **Cause**: Wrong baseDirectory
- **Fix**: Ensure baseDirectory is frontend/build

## 📋 Files to Check/Update

### 1. Update amplify.yml (if needed)
```yaml
version: 1
applications:
  - frontend:
      phases:
        preBuild:
          commands:
            - cd frontend
            - nvm use 18
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
    appRoot: frontend
```

### 2. Create frontend/.env
```
DISABLE_ESLINT_PLUGIN=true
ESLINT_NO_DEV_ERRORS=true
CI=false
```

### 3. Verify package.json dependencies
```json
{
  "dependencies": {
    "axios": "^1.10.0",
    "lucide-react": "^0.525.0",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-scripts": "5.0.1",
    "web-vitals": "^2.1.4"
  }
}
```

## 🎯 RECOMMENDED IMMEDIATE ACTION

**Use Manual Upload (Step 1) first** to get your app working quickly, then fix Git deployment later.

The manual upload with `ncdhhs-frontend-FIXED.zip` should work immediately since we've already tested the build locally.

Once that's working, we can troubleshoot the Git deployment issues separately.
