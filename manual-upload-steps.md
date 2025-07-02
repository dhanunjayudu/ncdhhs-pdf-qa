# 🚀 Manual Upload to AWS Amplify - Step by Step

## Current Status
- ❌ URL not working: https://staging.duisk83gae5d8.amplifyapp.com/
- ✅ Fresh build created: ncdhhs-frontend-build-v2.zip (168K)

## 🎯 Quick Fix Steps

### Option 1: Fix Current App
1. **Go to AWS Amplify Console**: https://console.aws.amazon.com/amplify/
2. **Find your app** (should be listed there)
3. **Click on the app name**
4. **Go to "Hosting" tab**
5. **Click "Deploy updates"**
6. **Upload the new file**: `ncdhhs-frontend-build-v2.zip`

### Option 2: Create New App (Recommended)
1. **Go to AWS Amplify Console**: https://console.aws.amazon.com/amplify/
2. **Click "New app" → "Host web app"**
3. **Choose "Deploy without Git provider"**
4. **Fill in details**:
   - App name: `ncdhhs-pdf-qa-frontend`
   - Environment name: `production`
   - Upload file: `ncdhhs-frontend-build-v2.zip`

5. **Set Environment Variables** (Important!):
   ```
   REACT_APP_API_URL = http://ncdhhs-pdf-qa-dev-alb-940310890.us-east-1.elb.amazonaws.com
   REACT_APP_ENVIRONMENT = production
   REACT_APP_VERSION = 4.0.0
   ```

6. **Click "Save and deploy"**

## 🔍 What to Check After Deployment

### 1. Build Logs
- Check the build logs in Amplify Console
- Look for any error messages
- Verify all files were uploaded correctly

### 2. Test URLs
Once deployed, test these URLs (replace with your actual domain):
- `https://your-domain.amplifyapp.com/` - Should show the main app
- `https://your-domain.amplifyapp.com/static/js/main.*.js` - Should load JavaScript
- `https://your-domain.amplifyapp.com/static/css/main.*.css` - Should load CSS

### 3. Browser Developer Tools
- Open browser developer tools (F12)
- Check Console tab for JavaScript errors
- Check Network tab for failed requests
- Look for 404 errors on static files

## 🚨 Common Issues and Solutions

### Issue 1: Still getting 404
**Cause**: Wrong base directory or file structure
**Solution**: 
- In Amplify Console, check "Build settings"
- Ensure artifacts baseDirectory is set correctly
- Try re-uploading the zip file

### Issue 2: App loads but API calls fail
**Cause**: Environment variables not set
**Solution**: 
- Add environment variables in Amplify Console
- Redeploy the app after adding variables

### Issue 3: CSS/JS files not loading
**Cause**: Incorrect file paths
**Solution**: 
- Check if static files are in the zip
- Verify the build was created correctly

## 📞 If You Need Help

If you're still having issues:
1. **Check Amplify Console build logs** - they'll show the exact error
2. **Try the browser developer tools** - look for specific error messages
3. **Share the error messages** - I can help debug specific issues

## 📦 Files Ready for Upload
- ✅ `ncdhhs-frontend-build-v2.zip` (168K) - Fresh build with production config
- ✅ `amplify.yml` - Updated build configuration
- ✅ Environment variables documented above
