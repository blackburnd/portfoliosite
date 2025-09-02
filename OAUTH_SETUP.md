# Google OAuth Setup Guide

## Current Issue
The OAuth login is failing with a "CSRF state mismatch" error because the Google OAuth credentials are not properly configured.

## Required Environment Variables

Add these to your `.env` file or set them as environment variables:

```bash
# Google OAuth Configuration
GOOGLE_CLIENT_ID=your-actual-google-client-id
GOOGLE_CLIENT_SECRET=your-actual-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/callback

# For production, use your domain:
# GOOGLE_REDIRECT_URI=https://blackburnsystems.com/auth/callback

# Authorized admin emails (comma-separated)
AUTHORIZED_EMAILS=your-email@gmail.com,another-admin@gmail.com

# Session secret key
SECRET_KEY=your-secure-random-secret-key
```

## Setting up Google OAuth

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google+ API or Google OAuth2 API
4. Go to "Credentials" → "Create Credentials" → "OAuth 2.0 Client IDs"
5. Choose "Web application" as the application type
6. Add these authorized redirect URIs:
   - `http://localhost:8000/auth/callback` (for development)
   - `https://blackburnsystems.com/auth/callback` (for production)
7. Copy the Client ID and Client Secret to your `.env` file

## Testing OAuth

Once configured, you can test the OAuth flow:

1. Start the server: `python -m uvicorn main:app --reload --port 8000`
2. Visit: `http://localhost:8000/auth/login`
3. You should be redirected to Google for authentication
4. After successful login, you'll be redirected back to the admin area

## Current Status

The OAuth implementation has been improved with:
- ✅ Better CSRF state validation
- ✅ Improved error handling
- ✅ Proper session management
- ❌ Missing actual Google OAuth credentials (need to be configured)

## Next Steps

1. Configure the Google OAuth credentials in Google Cloud Console
2. Update the `.env` file with the actual values
3. Test the OAuth flow
4. Deploy the updated configuration to production
