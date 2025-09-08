# Google OAuth Authentication Setup

## Overview

Your portfolio site now uses **Google OAuth 2.0** for secure admin authentication. This replaces the basic HTTP authentication with Google account-based login, providing enterprise-grade security.

## 🚀 Quick Setup

### 1. Run the Setup Script
```bash
./venv/bin/python google_oauth_setup.py
```

### 2. Configure Google Cloud Console

1. **Go to Google Cloud Console**: https://console.cloud.google.com/
2. **Create/Select Project**: Use existing project or create new one
3. **Enable APIs**:
   - APIs & Services → Library
   - Enable "Google+ API" and "People API"

4. **Create OAuth Credentials**:
   - APIs & Services → Credentials
   - Create Credentials → OAuth 2.0 Client IDs
   - Application type: Web application
   - Name: "Portfolio Admin Access"

5. **Configure Authorized URIs**:
   ```
   Development:
   - JavaScript origins: http://localhost:8000
   - Redirect URIs: http://localhost:8000/auth/callback
   
   Production:
   - JavaScript origins: https://yourdomain.com
   - Redirect URIs: https://yourdomain.com/auth/callback
   ```

6. **Copy Credentials** and update `.env`:
   ```bash
   GOOGLE_CLIENT_ID=123456789-abc.googleusercontent.com
   GOOGLE_CLIENT_SECRET=GOCSPX-your-secret-here
   GOOGLE_REDIRECT_URI=http://localhost:8000/auth/callback
   AUTHORIZED_EMAILS=blackburnd@gmail.com,trusted@gmail.com
   ```

## 🔒 How It Works

### Authentication Flow
1. User visits admin page (`/workadmin`)
2. System checks for valid authentication cookie
3. If not authenticated, redirects to Google OAuth (`/auth/login`)
4. User logs in with Google account
5. Google redirects back with authorization code
6. System verifies email is in authorized list
7. Creates JWT token and sets secure cookie
8. User can access admin pages

### Route Protection
- **Admin Pages**: Use cookie-based auth (seamless web experience)
- **API Endpoints**: Use Bearer token auth (for programmatic access)

### Security Features
- ✅ JWT tokens with expiration (8 hours)
- ✅ Email-based authorization whitelist
- ✅ Secure HTTP-only cookies
- ✅ CSRF protection via SameSite cookies
- ✅ Automatic token refresh

## 🎯 Usage

### Browser Access
1. Visit any admin page: `http://localhost:8000/workadmin`
2. Automatically redirects to Google login
3. After successful login, redirected back to admin page
4. Cookie maintains session for 8 hours

### API Access (Programmatic)
```javascript
// Get token (one-time setup)
const response = await fetch('/auth/login');
// Follow OAuth flow to get token

// Use token for API calls
const apiResponse = await fetch('/workitems', {
    method: 'POST',
    headers: {
        'Authorization': 'Bearer your-jwt-token-here',
        'Content-Type': 'application/json'
    },
    body: JSON.stringify(workItem)
});
```

### Logout
Visit: `http://localhost:8000/auth/logout`

## 🛡️ Security Configuration

### Authorized Users
Only emails listed in `AUTHORIZED_EMAILS` can access admin functions:
```bash
AUTHORIZED_EMAILS=blackburnd@gmail.com,admin@company.com,trusted@gmail.com
```

### Production Settings
For production deployment, update `.env`:
```bash
GOOGLE_REDIRECT_URI=https://yourdomain.com/auth/callback
# Add your production domain to Google OAuth settings
```

## 🚀 Deployment to Google Cloud

### Environment Variables
Set these in your Google Cloud instance:
```bash
# SSH into your instance
gcloud compute ssh your-instance-name

# Set environment variables
export GOOGLE_CLIENT_ID="your-client-id.googleusercontent.com"
export GOOGLE_CLIENT_SECRET="your-client-secret"
export GOOGLE_REDIRECT_URI="https://yourdomain.com/auth/callback"
export AUTHORIZED_EMAILS="blackburnd@gmail.com"

# Or add to systemd service
sudo systemctl edit portfolio.service
```

### Systemd Service Configuration
```ini
[Service]
Environment="GOOGLE_CLIENT_ID=your-client-id.googleusercontent.com"
Environment="GOOGLE_CLIENT_SECRET=your-client-secret"
Environment="GOOGLE_REDIRECT_URI=https://yourdomain.com/auth/callback"
Environment="AUTHORIZED_EMAILS=blackburnd@gmail.com"
```

## 🔧 Troubleshooting

### Common Issues

**"OAuth not configured" error**:
- Verify `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are set
- Check `.env` file format (no spaces around `=`)

**"Access denied" after Google login**:
- Verify your Gmail address is in `AUTHORIZED_EMAILS`
- Check for typos in email addresses

**"Invalid redirect URI" error**:
- Ensure redirect URI in Google Console matches `GOOGLE_REDIRECT_URI`
- For localhost: `http://localhost:8000/auth/callback`
- For production: `https://yourdomain.com/auth/callback`

**Authentication loop (keeps redirecting)**:
- Clear browser cookies
- Check JWT token expiration
- Verify system clock is correct

### Testing Commands
```bash
# Test configuration
./venv/bin/python google_oauth_setup.py

# Check auth status endpoint
curl http://localhost:8000/auth/status

# Test admin access (should redirect to Google)
curl -v http://localhost:8000/workadmin
```

## 📊 Current Protection Status

✅ **Protected Routes:**
- `/workadmin` - Work admin interface
- `/workadmin/bulk` - Bulk work management  
- `/projectsadmin` - Projects admin interface
- `/projectsadmin/bulk` - Bulk projects management
- All POST/PUT/DELETE API endpoints

✅ **Public Routes:**
- `/` - Home page
- `/work` - Work experience listing
- `/projects` - Projects listing
- `/contact` - Contact page
- All GET endpoints for reading data

## 🎉 Benefits Over Basic Auth

1. **No shared passwords** - Each admin uses their own Google account
2. **2FA support** - If enabled on Google account, automatically applies
3. **Audit trail** - Know exactly which Google account performed actions
4. **Automatic security** - Google handles password policies, breach detection
5. **Easy user management** - Add/remove access by email address
6. **Session management** - Automatic token expiration and refresh

Your admin panel is now secured with enterprise-grade Google OAuth authentication! 🔐
