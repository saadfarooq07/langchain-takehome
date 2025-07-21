# Google OAuth Setup Guide

This guide will help you set up Google OAuth for Allogator.

## Prerequisites

1. A Google Cloud Console account
2. A project in Google Cloud Console

## Setup Steps

### 1. Create OAuth 2.0 Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project or create a new one
3. Navigate to **APIs & Services** > **Credentials**
4. Click **Create Credentials** > **OAuth client ID**
5. If prompted, configure the OAuth consent screen first:
   - Choose "External" for user type
   - Fill in the required fields (app name, support email, etc.)
   - Add your domain to authorized domains
   - Save and continue

### 2. Configure OAuth Client

1. For Application type, select **Web application**
2. Name your OAuth client (e.g., "Allogator Web Client")
3. Add Authorized JavaScript origins:
   - `http://localhost:3000` (for development)
   - `https://yourdomain.com` (for production)
4. Add Authorized redirect URIs:
   - `http://localhost:3000/auth/callback` (for development)
   - `https://yourdomain.com/auth/callback` (for production)
5. Click **Create**

### 3. Save Your Credentials

After creating the OAuth client, you'll receive:
- **Client ID**: This goes in your frontend `.env` file
- **Client Secret**: Keep this secure (not needed for frontend)

### 4. Configure Environment Variables

#### Frontend (.env)
```bash
REACT_APP_GOOGLE_CLIENT_ID=your-client-id-here.apps.googleusercontent.com
```

#### Backend (.env)
```bash
GOOGLE_CLIENT_ID=your-client-id-here.apps.googleusercontent.com
```

### 5. Apply Database Migration

Run the migration to add Google OAuth support:

```bash
psql -U loganalyzer -d loganalyzer -f scripts/add_google_oauth.sql
```

## Testing

1. Start your backend server
2. Start your frontend development server
3. Navigate to the signup or login page
4. Click "Sign up with Google" or "Sign in with Google"
5. Complete the Google authentication flow

## Security Considerations

1. **Never expose your Client Secret** - It should only be stored on the backend
2. **Use HTTPS in production** - OAuth requires secure connections
3. **Validate tokens on the backend** - Always verify Google tokens server-side
4. **Implement proper session management** - Use secure, httpOnly cookies for sessions

## Troubleshooting

### "Invalid token audience" error
- Ensure the Client ID in your frontend matches the one in your backend

### "Redirect URI mismatch" error
- Check that your redirect URIs in Google Console match exactly
- Include the protocol (http/https) and any trailing slashes

### "Google OAuth not configured" error
- Ensure GOOGLE_CLIENT_ID is set in your backend environment variables

## Additional Features

You can request additional scopes for more user information:
- `profile` - Basic profile info (included by default)
- `email` - Email address (included by default)
- `openid` - OpenID Connect authentication

To add scopes, modify the GoogleLogin component:
```jsx
<GoogleLogin
  scope="openid profile email"
  // ... other props
/>
```