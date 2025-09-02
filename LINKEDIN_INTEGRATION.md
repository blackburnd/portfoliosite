# LinkedIn API Integration Setup

## Overview

Your portfolio site now includes **LinkedIn API integration** that allows authenticated administrators to automatically sync their LinkedIn profile and work experience data to the portfolio database. This feature provides:

- **Automatic profile sync**: Update portfolio bio, title, and tagline from LinkedIn
- **Work experience sync**: Import LinkedIn work history to the portfolio database
- **Admin-controlled**: Only authenticated administrators can trigger sync operations
- **Secure**: Uses existing Google OAuth admin authentication system

## 🚀 Quick Setup

### 1. Configure LinkedIn Credentials

Add the following environment variables to your system:

```bash
# LinkedIn Account Credentials
LINKEDIN_USERNAME=your_email@example.com
LINKEDIN_PASSWORD=your_linkedin_password

# Optional: Target Profile ID (defaults to 'blackburnd')
LINKEDIN_PROFILE_ID=your_linkedin_profile_id
```

**⚠️ Security Note**: LinkedIn credentials should be stored securely. Consider using:
- Environment variables in production
- Secure credential management systems
- App-specific passwords if your LinkedIn account has 2FA enabled

### 2. Access LinkedIn Sync Admin

1. **Login as Admin**: Use the existing Google OAuth admin login at `/auth/login`
2. **Navigate to LinkedIn Sync**: Visit `/linkedin` or use the "🔗 LinkedIn Sync" link in the admin navigation
3. **Check Configuration**: The page will show your configuration status
4. **Sync Data**: Use the provided buttons to sync profile and/or experience data

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