# LinkedIn OAuth Implementation - Deployment Guide

## Overview
This implementation replaces environment variable-based LinkedIn authentication with secure OAuth 2.0 flow, following best practices:

1. **Google-only Authentication**: Admin users authenticate with Google OAuth
2. **Optional LinkedIn Connection**: Admins can choose to connect their LinkedIn account via OAuth
3. **Secure Token Storage**: LinkedIn tokens are encrypted and stored in database, associated with Google account
4. **Persistent Connectivity**: Tokens are automatically refreshed for subsequent API calls

## What Was Implemented

### 1. New Services
- **`oauth_manager.py`**: Unified OAuth management service for LinkedIn authentication
- **`linkedin_data_sync.py`**: Enhanced LinkedIn data synchronization service using OAuth

### 2. Updated Files
- **`main.py`**: Updated LinkedIn admin routes to use new OAuth manager
- **`templates/linkedin_admin.html`**: Redesigned admin interface for OAuth flow
- **`sql/linkedin_oauth_migration.sql`**: Database schema for LinkedIn OAuth credentials

### 3. Database Schema
```sql
-- Table: linkedin_oauth_credentials
-- Stores encrypted LinkedIn OAuth tokens associated with admin Google accounts
CREATE TABLE linkedin_oauth_credentials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    admin_email VARCHAR(100) NOT NULL UNIQUE,
    access_token TEXT NOT NULL,        -- Encrypted
    refresh_token TEXT,                -- Encrypted  
    token_expires_at TIMESTAMP WITH TIME ZONE,
    linkedin_profile_id VARCHAR(100),
    scope TEXT DEFAULT 'r_liteprofile r_emailaddress',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

## Environment Variables Required

### For Production
```bash
# LinkedIn OAuth Configuration
LINKEDIN_CLIENT_ID=your_linkedin_client_id
LINKEDIN_CLIENT_SECRET=your_linkedin_client_secret
LINKEDIN_REDIRECT_URI=https://yourdomain.com/admin/linkedin/callback

# Token Encryption (generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
OAUTH_ENCRYPTION_KEY=your_generated_encryption_key

# Existing Google OAuth (already configured)
GOOGLE_CLIENT_ID=existing_value
GOOGLE_CLIENT_SECRET=existing_value
GOOGLE_REDIRECT_URI=existing_value
AUTHORIZED_EMAILS=existing_value
SECRET_KEY=existing_value
```

## LinkedIn OAuth App Setup

1. Go to [LinkedIn Developer Portal](https://www.linkedin.com/developers/)
2. Create new app or use existing app
3. Configure OAuth 2.0 settings:
   - **Authorized Redirect URLs**: `https://yourdomain.com/admin/linkedin/callback`
   - **Required Scopes**: 
     - `r_liteprofile` (read basic profile)
     - `r_emailaddress` (read email address)

## Deployment Steps

### 1. Deploy Code
```bash
git add .
git commit -m "Implement LinkedIn OAuth 2.0 authentication"
git push origin main
```

### 2. Set Environment Variables
Set the LinkedIn OAuth and encryption environment variables in your production environment.

### 3. Create Database Table
The `linkedin_oauth_credentials` table will be created automatically when the first OAuth connection is attempted, or you can run the migration manually.

### 4. Admin Reconnection
After deployment, admin users will need to:
1. Log in with their Google account (existing flow)
2. Go to LinkedIn admin page (`/linkedin`)
3. Click "Connect LinkedIn" to start OAuth flow
4. Authorize the application on LinkedIn
5. Start using the new sync features

## Key Features

### Admin Experience
1. **Single Sign-On**: Only Google login required for admin access
2. **Optional LinkedIn**: LinkedIn connection is optional and can be done anytime
3. **Secure Storage**: LinkedIn tokens are encrypted and auto-refreshed
4. **Easy Management**: Connect/disconnect LinkedIn from admin interface

### Security Improvements
- ✅ No LinkedIn credentials in environment variables
- ✅ Encrypted token storage
- ✅ Automatic token refresh
- ✅ Secure OAuth 2.0 flow
- ✅ Read-only LinkedIn access
- ✅ Per-admin token isolation

### Backward Compatibility
- ✅ Existing Google OAuth flow unchanged
- ✅ Portfolio database schema unchanged  
- ✅ Admin interface maintains same functionality
- ✅ Graceful fallback if LinkedIn not connected

## Testing Checklist

### Before Deployment
- [x] New modules import successfully
- [x] LinkedIn admin page loads
- [x] OAuth manager handles missing credentials gracefully

### After Deployment
- [ ] Google OAuth login works (existing functionality)
- [ ] LinkedIn admin page shows "Connect LinkedIn" option
- [ ] LinkedIn OAuth flow redirects correctly
- [ ] Tokens are stored encrypted in database
- [ ] LinkedIn sync operations work with OAuth tokens
- [ ] Token refresh works automatically
- [ ] Disconnect functionality works

## Rollback Plan
If issues occur:
1. Environment variables can be temporarily restored
2. Old `linkedin_sync.py` can be used as fallback
3. Database table can be dropped without affecting portfolio data
4. OAuth routes can be disabled via feature flag

## Benefits Over Previous Implementation
1. **Security**: No credentials in environment variables
2. **Scalability**: Each admin has their own LinkedIn tokens
3. **Maintenance**: Automatic token refresh, no manual credential management
4. **User Experience**: Simple OAuth flow, clear connection status
5. **Compliance**: Follows OAuth 2.0 best practices
