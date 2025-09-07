# auth.py - Google OAuth Authentication Module
import os
import json
from typing import Optional, List
from datetime import datetime, timedelta
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from authlib.integrations.starlette_client import OAuth
from authlib.integrations.starlette_client import OAuthError
from jose import jwt, JWTError
import secrets

# Configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET") 
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "https://www.blackburnsystems.com/auth/callback")
SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480  # 8 hours

# Authorized emails - load from environment
AUTHORIZED_EMAILS = os.getenv("AUTHORIZED_EMAILS", "").split(",")
AUTHORIZED_EMAILS = [email.strip() for email in AUTHORIZED_EMAILS if email.strip()]

# OAuth setup
oauth = OAuth()

if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
    try:
        oauth.register(
            name='google',
            client_id=GOOGLE_CLIENT_ID,
            client_secret=GOOGLE_CLIENT_SECRET,
            server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
            client_kwargs={
                'scope': 'openid email profile '
                         'https://www.googleapis.com/auth/gmail.send'
            }
        )
        print(f"✅ OAuth registered successfully with client ID: {GOOGLE_CLIENT_ID[:10]}...")
    except Exception as e:
        print(f"❌ OAuth registration failed: {e}")
        oauth = None
else:
    print("❌ Missing GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET")
    oauth = None

# Security bearer for JWT tokens
security = HTTPBearer(auto_error=False)


class AuthenticationError(Exception):
    """Custom authentication error"""
    pass


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token"""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info("=== Token Creation Debug ===")
    logger.info(f"Creating token for data: {data}")
    logger.info(f"SECRET_KEY configured: {bool(SECRET_KEY)}")
    logger.info(f"SECRET_KEY length: {len(SECRET_KEY) if SECRET_KEY else 0}")
    
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    logger.info(f"Token payload: {to_encode}")
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    logger.info(f"Created JWT token (first 50 chars): {encoded_jwt[:50] if encoded_jwt else 'None'}")
    return encoded_jwt


def verify_token(token: str) -> dict:
    """Verify and decode JWT token"""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info("=== Token Verification Debug ===")
    logger.info(f"SECRET_KEY configured: {bool(SECRET_KEY)}")
    logger.info(f"SECRET_KEY length: {len(SECRET_KEY) if SECRET_KEY else 0}")
    logger.info(f"Token to verify (first 50 chars): {token[:50] if token else 'None'}")
    
    try:
        payload = jwt.decode(
            token, 
            SECRET_KEY, 
            algorithms=[ALGORITHM],
            options={"verify_aud": False}  # Don't verify audience for now
        )
        email: str = payload.get("sub")
        logger.info(f"JWT decoded successfully, email: {email}")
        
        if email is None:
            logger.error("No email (sub) found in JWT payload")
            raise AuthenticationError("Invalid token")
        return payload
    except JWTError as e:
        logger.error(f"JWT decoding failed: {str(e)}")
        raise AuthenticationError("Invalid token")


def is_authorized_user(email: str) -> bool:
    """Check if email is in authorized list"""
    return email in AUTHORIZED_EMAILS


async def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> dict:
    """Get current authenticated user from JWT token"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        payload = verify_token(credentials.credentials)
        email = payload.get("sub")
        
        if not email or not is_authorized_user(email):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. User not authorized."
            )
        
        return payload
    except AuthenticationError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def require_admin_auth(user: dict = Depends(get_current_user)) -> dict:
    """Require admin authentication for protected routes"""
    return user


def get_oauth_client():
    """Get configured OAuth client"""
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google OAuth not configured"
        )
    return oauth.google


def get_login_url(request: Request) -> str:
    """Get Google OAuth login URL"""
    google = get_oauth_client()
    redirect_uri = GOOGLE_REDIRECT_URI
    # Handle both direct and reverse proxy scenarios
    base_url = str(request.base_url)
    return f"{base_url}auth/login"


def create_user_session(user_info: dict) -> dict:
    """Create user session data from Google user info"""
    return {
        "sub": user_info.get("email"),
        "name": user_info.get("name"),
        "email": user_info.get("email"),
        "picture": user_info.get("picture"),
        "iss": "google",
        "aud": GOOGLE_CLIENT_ID,
        "iat": datetime.utcnow().timestamp(),
    }


def get_auth_status():
    """Get authentication configuration status"""
    return {
        "google_oauth_configured": bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET),
        "authorized_emails_count": len(AUTHORIZED_EMAILS),
        "redirect_uri": GOOGLE_REDIRECT_URI
    }
