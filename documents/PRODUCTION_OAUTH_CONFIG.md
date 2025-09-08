# Production OAuth Configuration Issue

## Problem
When clicking the login button on production (https://www.blackburnsystems.com), users are redirected directly to `/workadmin` instead of initiating the Google OAuth flow.

## Root Cause
The production environment likely has the wrong `GOOGLE_REDIRECT_URI` configuration.

## Current Configuration (Local)
```
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/callback
```

## Required Production Configuration
```
GOOGLE_REDIRECT_URI=https://www.blackburnsystems.com/auth/callback
```

## Google OAuth Console Configuration
In the Google Cloud Console OAuth 2.0 Client IDs, ensure these redirect URIs are added:
- `https://www.blackburnsystems.com/auth/callback` (production)
- `http://localhost:8000/auth/callback` (development)

## Steps to Fix
1. Update the production environment variable:
   ```
   GOOGLE_REDIRECT_URI=https://www.blackburnsystems.com/auth/callback
   ```

2. Verify Google OAuth console has the production redirect URI configured

3. Test the OAuth flow in production

## Testing
1. Visit https://www.blackburnsystems.com
2. Click the "Login" button in the top-right
3. Should redirect to Google OAuth instead of directly to /workadmin
