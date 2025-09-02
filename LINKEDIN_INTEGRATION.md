# LinkedIn OAuth 2.0 Integration Setup

## Overview

Your portfolio site now includes **LinkedIn OAuth 2.0 integration** that allows authenticated administrators to securely connect their LinkedIn account and automatically sync profile and work experience data to the portfolio database. This feature provides:

- **🔐 Secure OAuth 2.0 Authentication**: Replace environment variables with secure token-based authentication
- **📊 Automatic profile sync**: Update portfolio bio, title, and tagline from LinkedIn
- **💼 Work experience sync**: Import LinkedIn work history to the portfolio database
- **🛡️ Admin-controlled**: Only authenticated administrators can manage LinkedIn connections
- **🔄 Persistent Connectivity**: Tokens are stored securely for ongoing sync operations
- **♻️ Token Refresh**: Automated token refresh for continuous access
- **🔙 Legacy Support**: Backward compatible with environment variable method

## 🚀 Quick Setup

### 1. Configure LinkedIn OAuth 2.0

Create a LinkedIn OAuth application and set environment variables:

```bash
# Required LinkedIn OAuth Configuration
export LINKEDIN_CLIENT_ID="your_linkedin_client_id"
export LINKEDIN_CLIENT_SECRET="your_linkedin_client_secret"
export LINKEDIN_REDIRECT_URI="https://yourdomain.com/linkedin/oauth/callback"

# Required for secure token storage
export LINKEDIN_ENCRYPTION_KEY="your_32_character_encryption_key"
```

### 2. Set Up Database

Run the LinkedIn OAuth migration:

```sql
-- Run against your PostgreSQL database
\i sql/linkedin_oauth_migration.sql
```

### 3. Connect Your LinkedIn Account

1. **Admin Login**: Authenticate using Google OAuth admin system
2. **Navigate to LinkedIn Admin**: Visit `/linkedin` admin page
3. **Connect Account**: Click "🔗 Connect LinkedIn Account" button
4. **Authorize Access**: Complete LinkedIn OAuth authorization
5. **Start Syncing**: Use sync buttons to import your LinkedIn data

## 🔧 LinkedIn OAuth Setup

### Create LinkedIn OAuth Application

1. Go to [LinkedIn Developer Portal](https://developer.linkedin.com/)
2. Click "Create App" and fill in your application details
3. In the "Auth" tab, configure OAuth 2.0 settings:
   - **Authorized Redirect URLs**: Add `https://yourdomain.com/linkedin/oauth/callback`
   - **OAuth 2.0 scopes**: Request `r_liteprofile` and `r_emailaddress`
4. Copy your `Client ID` and `Client Secret` to your environment variables

### Environment Variables

```bash
# LinkedIn OAuth 2.0 Configuration (Required)
LINKEDIN_CLIENT_ID=your_app_client_id
LINKEDIN_CLIENT_SECRET=your_app_client_secret
LINKEDIN_REDIRECT_URI=https://yourdomain.com/linkedin/oauth/callback

# Secure Token Storage (Required)
LINKEDIN_ENCRYPTION_KEY=your_32_character_base64_encryption_key

# Legacy Support (Deprecated - use OAuth instead)
LINKEDIN_USERNAME=your_linkedin_email  # ⚠️ Deprecated
LINKEDIN_PASSWORD=your_linkedin_password  # ⚠️ Deprecated
LINKEDIN_PROFILE_ID=your_profile_id  # Optional, defaults to 'blackburnd'
```

### Generate Encryption Key

Generate a secure encryption key for token storage:

```python
from cryptography.fernet import Fernet
key = Fernet.generate_key()
print(f"LINKEDIN_ENCRYPTION_KEY={key.decode()}")
```

## 🔄 Available Sync Operations

### Profile Sync (`POST /linkedin/sync/profile`)
- Updates portfolio `name`, `title`, `bio`, and `tagline` from LinkedIn profile
- Maps LinkedIn `firstName` + `lastName` → portfolio `name`
- Maps LinkedIn `headline` → portfolio `title` and `tagline`
- Maps LinkedIn `summary` → portfolio `bio`

### Experience Sync (`POST /linkedin/sync/experience`)
- **⚠️ Warning**: Replaces ALL existing work experience entries
- Imports LinkedIn work history to `work_experience` table
- Maps LinkedIn company, position, location, dates, and descriptions
- Automatically detects current vs. past positions
- Sets appropriate sort order

### Full Sync (`POST /linkedin/sync/full`)
- Performs both profile and experience sync in sequence
- Returns combined results with error handling
- Recommended for initial setup

## 📊 Data Mapping

### LinkedIn Profile → Portfolio Fields

| LinkedIn Field | Portfolio Field | Notes |
|---------------|----------------|-------|
| `firstName` + `lastName` | `name` | Combined full name |
| `headline` | `title` | Professional title |
| `headline` | `tagline` | Same as title |
| `summary` | `bio` | Profile description |
| `locationName` | *(not stored)* | Location info available but not used |

### LinkedIn Experience → Work Experience Fields

| LinkedIn Field | Work Experience Field | Notes |
|---------------|----------------------|-------|
| `companyName` | `company` | Company name |
| `title` | `position` | Job title/position |
| `locationName` | `location` | Work location |
| `timePeriod.startDate` | `start_date` | Format: `YYYY-MM` |
| `timePeriod.endDate` | `end_date` | Format: `YYYY-MM` or NULL |
| `description` | `description` | Job description |
| *(calculated)* | `is_current` | TRUE if no end date |
| `companyUrn` | `company_url` | Company URL (if available) |
| *(auto-generated)* | `sort_order` | Sequential ordering |

## 🛡️ Security & Authentication

### Access Control
- **Admin Only**: All LinkedIn sync endpoints require admin authentication
- **Google OAuth**: Uses existing Google OAuth system for authentication
- **Session-based**: Maintains admin session security

### Protected Endpoints
- `GET /linkedin/status` - Configuration status (admin-only)
- `POST /linkedin/sync/profile` - Profile sync (admin-only)
- `POST /linkedin/sync/experience` - Experience sync (admin-only)
- `POST /linkedin/sync/full` - Full sync (admin-only)
- `GET /linkedin` - Admin interface (admin-only)

### Public Endpoints
All existing public endpoints remain unchanged and don't require LinkedIn credentials.

## 🔧 Troubleshooting

### Common Issues

#### 1. "LinkedIn credentials not configured"
**Solution**: Set `LINKEDIN_USERNAME` and `LINKEDIN_PASSWORD` environment variables

#### 2. "LinkedIn authentication failed"
**Possible causes**:
- Incorrect username/password
- LinkedIn account locked or requires verification
- Two-factor authentication blocking programmatic access

**Solutions**:
- Verify credentials
- Check LinkedIn account status
- Consider using app-specific password
- Temporarily disable 2FA for API access

#### 3. "Profile sync failed: Portfolio not found"
**Solution**: Ensure the target portfolio exists in the database with ID `daniel-blackburn`

#### 4. "Experience sync partially failed"
**Cause**: Some LinkedIn experience entries may have incomplete data
**Solution**: Check sync results for specific error details

### Environment Variables Debug

Use the LinkedIn Sync admin page to check configuration status:
- **LinkedIn API**: Shows if credentials are configured
- **Username**: Shows configured LinkedIn username (without password)
- **Target Profile ID**: Shows which LinkedIn profile will be synced
- **Portfolio ID**: Shows target portfolio in database

## 📋 API Reference

### GET /linkedin/status
Returns LinkedIn sync configuration status.

**Response**:
```json
{
  "status": "success",
  "linkedin_sync": {
    "linkedin_configured": true,
    "linkedin_username": "user@example.com",
    "target_profile_id": "blackburnd",
    "portfolio_id": "daniel-blackburn"
  }
}
```

### POST /linkedin/sync/profile
Syncs LinkedIn profile data to portfolio.

**Response**:
```json
{
  "status": "success",
  "result": {
    "status": "success",
    "updated_fields": ["name", "title", "bio", "tagline"],
    "profile_data": { ... }
  }
}
```

### POST /linkedin/sync/experience
Syncs LinkedIn work experience to database.

**Response**:
```json
{
  "status": "success",
  "result": {
    "status": "success",
    "experiences_count": 3,
    "experiences": [ ... ]
  }
}
```

### POST /linkedin/sync/full
Performs complete sync of profile and experience data.

**Response**:
```json
{
  "status": "success",
  "result": {
    "status": "success",
    "sync_timestamp": "2024-01-01T12:00:00",
    "profile_sync": { ... },
    "experience_sync": { ... },
    "errors": []
  }
}
```

## 🚀 Production Deployment

### Environment Variables
Set these in your production environment:

```bash
# Required for LinkedIn sync
export LINKEDIN_USERNAME="your_email@example.com"
export LINKEDIN_PASSWORD="your_secure_password"
export LINKEDIN_PROFILE_ID="your_profile_id"  # Optional

# Existing OAuth variables (already configured)
export GOOGLE_CLIENT_ID="your-google-client-id"
export GOOGLE_CLIENT_SECRET="your-google-client-secret"
export AUTHORIZED_EMAILS="admin@example.com"
```

### Systemd Service Configuration
Add LinkedIn environment variables to your systemd service:

```ini
[Service]
Environment="LINKEDIN_USERNAME=your_email@example.com"
Environment="LINKEDIN_PASSWORD=your_secure_password"
Environment="LINKEDIN_PROFILE_ID=your_profile_id"
```

### Docker Deployment
Add to your Docker environment:

```yaml
environment:
  - LINKEDIN_USERNAME=your_email@example.com
  - LINKEDIN_PASSWORD=your_secure_password
  - LINKEDIN_PROFILE_ID=your_profile_id
```

## 🎯 Usage Workflow

1. **Initial Setup**: Configure LinkedIn credentials in environment
2. **Admin Login**: Authenticate using Google OAuth admin system
3. **Access Sync Interface**: Navigate to `/linkedin` admin page
4. **Verify Configuration**: Check that LinkedIn credentials are properly configured
5. **Perform Initial Sync**: Run "Full Sync" to import all data
6. **Regular Updates**: Use individual profile or experience sync as needed
7. **Monitor Results**: Review sync results and handle any errors

## 🔗 Integration with Existing System

This LinkedIn integration seamlessly integrates with your existing portfolio system:

- **Database Schema**: Uses existing `portfolios` and `work_experience` tables
- **Authentication**: Leverages existing Google OAuth admin system  
- **Admin Interface**: Consistent with existing admin page design
- **Navigation**: Added to existing admin navigation structure
- **Error Handling**: Follows existing error response patterns
- **Logging**: Uses existing application logging infrastructure

The integration is designed to be **non-intrusive** and **backward-compatible** with all existing functionality.