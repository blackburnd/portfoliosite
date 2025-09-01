#!/usr/bin/env python3
# google_oauth_setup.py - Setup script for Google OAuth configuration

import os
import secrets
import requests
from pathlib import Path

def generate_secret_key():
    """Generate a secure secret key"""
    return secrets.token_urlsafe(32)

def check_google_oauth_config():
    """Check if Google OAuth is properly configured"""
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/callback")
    authorized_emails = os.getenv("AUTHORIZED_EMAILS", "")
    
    print("=== Google OAuth Configuration Status ===")
    print(f"✓ Client ID: {'✓ Configured' if client_id else '✗ Missing'}")
    print(f"✓ Client Secret: {'✓ Configured' if client_secret else '✗ Missing'}")
    print(f"✓ Redirect URI: {redirect_uri}")
    print(f"✓ Authorized Emails: {authorized_emails or '✗ Not configured'}")
    
    if not client_id or not client_secret:
        print("\n⚠️  Google OAuth is not fully configured!")
        print("Please follow these steps to set up Google OAuth:")
        print_setup_instructions()
        return False
    
    print("\n✅ Google OAuth appears to be configured!")
    return True

def print_setup_instructions():
    """Print detailed setup instructions"""
    print("""
=== Google OAuth Setup Instructions ===

1. Go to Google Cloud Console:
   https://console.cloud.google.com/

2. Create a new project or select existing project

3. Enable Google+ API:
   - Go to "APIs & Services" > "Library"
   - Search for "Google+ API" and enable it
   - Also enable "People API" for user info

4. Create OAuth 2.0 Credentials:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth 2.0 Client IDs"
   - Choose "Web application"
   - Name: "Portfolio Admin Access"
   
5. Configure Authorized URIs:
   For development:
   - Authorized JavaScript origins: http://localhost:8000
   - Authorized redirect URIs: http://localhost:8000/auth/callback
   
   For production:
   - Authorized JavaScript origins: https://yourdomain.com
   - Authorized redirect URIs: https://yourdomain.com/auth/callback

6. Copy the credentials:
   - Client ID (ends with .googleusercontent.com)
   - Client Secret

7. Update your .env file with:
   GOOGLE_CLIENT_ID=your-client-id-here.googleusercontent.com
   GOOGLE_CLIENT_SECRET=your-client-secret-here
   AUTHORIZED_EMAILS=your.email@gmail.com,another@gmail.com

8. Restart your application

=== Security Notes ===
- Only add trusted email addresses to AUTHORIZED_EMAILS
- Keep your Client Secret secure and never commit it to version control
- Use HTTPS in production for secure authentication
""")

def update_env_file():
    """Help user update .env file"""
    env_path = Path(".env")
    
    print("\n=== Environment Configuration ===")
    
    if not env_path.exists():
        print("Creating .env file...")
        env_content = f"""# Google OAuth Configuration
GOOGLE_CLIENT_ID=your-google-client-id-here.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret-here
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/callback
AUTHORIZED_EMAILS=blackburnd@gmail.com

# Application Settings
SECRET_KEY={generate_secret_key()}
DATABASE_URL=your-database-url-here
"""
        env_path.write_text(env_content)
        print("✓ Created .env file with template values")
    else:
        print("✓ .env file already exists")
    
    print(f"📝 Please edit {env_path} and update the Google OAuth credentials")

def test_oauth_config():
    """Test if OAuth configuration is working"""
    try:
        from auth import get_auth_status
        status = get_auth_status()
        
        print("\n=== Configuration Test ===")
        print(f"Google OAuth Configured: {status['google_oauth_configured']}")
        print(f"Authorized Emails Count: {status['authorized_emails_count']}")
        print(f"Redirect URI: {status['redirect_uri']}")
        
        if status['google_oauth_configured']:
            print("✅ Authentication module loaded successfully!")
        else:
            print("❌ OAuth configuration incomplete")
            
    except Exception as e:
        print(f"❌ Error testing configuration: {e}")

def main():
    """Main setup function"""
    print("🔐 Google OAuth Setup for Portfolio Admin Panel")
    print("=" * 50)
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Check current configuration
    is_configured = check_google_oauth_config()
    
    if not is_configured:
        update_env_file()
        print("\n⚠️  Please update .env file with your Google OAuth credentials and restart")
        return
    
    # Test configuration
    test_oauth_config()
    
    print("\n🚀 Setup complete! You can now:")
    print("1. Start your application: ./venv/bin/uvicorn main:app --reload")
    print("2. Go to admin pages: http://localhost:8000/workadmin")
    print("3. You'll be redirected to Google login automatically")

if __name__ == "__main__":
    main()
