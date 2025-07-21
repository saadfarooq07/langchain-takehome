# Google OAuth Setup Guide

## Current Configuration
- **Client ID**: `872135203640-42nj7cv9mb7464hr53nhfmk6lfkv3a9j.apps.googleusercontent.com`
- **Frontend URL**: `http://localhost:3002`

## Required Google Cloud Console Settings

To fix the "Missing required parameter: client_id" error, ensure these settings in Google Cloud Console:

### 1. Go to Google Cloud Console
Visit: https://console.cloud.google.com/apis/credentials

### 2. Configure OAuth 2.0 Client
Find your OAuth 2.0 Client ID and click to edit it.

### 3. Add Authorized JavaScript Origins
Add these URLs:
- `http://localhost:3000`
- `http://localhost:3001`
- `http://localhost:3002`
- `http://localhost:3003`
- `http://127.0.0.1:3000`
- `http://127.0.0.1:3001`
- `http://127.0.0.1:3002`
- `http://127.0.0.1:3003`

### 4. Add Authorized Redirect URIs (if needed)
- `http://localhost:3002/auth/callback`
- `http://localhost:8000/auth/google/callback`

### 5. Save Changes
Click "Save" at the bottom of the page.

## Testing the Fix

1. **Hard refresh the browser**: Ctrl+Shift+R (or Cmd+Shift+R on Mac)
2. **Clear browser cache and cookies**
3. **Open Developer Console** to check if Client ID is loaded
4. **Try Sign in with Google** again

## Alternative Solutions

If the issue persists:

1. **Restart the frontend server**:
   ```bash
   # Stop the current server (Ctrl+C)
   # Start again
   npm start
   ```

2. **Check environment variables are loaded**:
   - Open browser console
   - Look for: "Google Client ID: 872135203640-..."

3. **Use a different Google account** or create a new OAuth client

## Creating Your Own OAuth Client (Optional)

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project or select existing
3. Enable Google+ API
4. Create OAuth 2.0 credentials
5. Update `.env` file with your new Client ID