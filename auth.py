# auth.py - Google OAuth Authentication Module
import os
from typing import Optional
from datetime import datetime, timedelta
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
import secrets
import logging

logger = logging.getLogger(__name__)

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480  # 8 hours

# Authorized emails - load from environment as fallback
authorized_emails_raw = os.getenv("AUTHORIZED_EMAILS", "")
print(f"DEBUG: Raw AUTHORIZED_EMAILS from env: '{authorized_emails_raw}'")
print(f"DEBUG: Length of raw string: {len(authorized_emails_raw)}")
print(f"DEBUG: Repr of raw string: {repr(authorized_emails_raw)}")

if authorized_emails_raw:
    AUTHORIZED_EMAILS = [
        email.strip() for email in authorized_emails_raw.split(" ") if email.strip()
    ]
else:
    AUTHORIZED_EMAILS = []

print(f"DEBUG: Parsed AUTHORIZED_EMAILS list: {AUTHORIZED_EMAILS}")
print(f"DEBUG: Number of authorized emails: {len(AUTHORIZED_EMAILS)}")

# Security bearer for JWT tokens
security = HTTPBearer(auto_error=False)


class AuthenticationError(Exception):
    """Custom authentication error"""
    pass


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> dict:
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"verify_aud": False}  # Don't verify audience for now
        )
        email: str = payload.get("sub")
        if email is None:
            raise AuthenticationError("Invalid token")
        return payload
    except JWTError:
        raise AuthenticationError("Invalid token")


def is_authorized_user(email: str) -> bool:
    """Check if email is in authorized list"""
    print(f"DEBUG: Checking authorization for email: '{email}'")
    print(f"DEBUG: Available AUTHORIZED_EMAILS: {AUTHORIZED_EMAILS}")
    
    result = email in AUTHORIZED_EMAILS
    print(f"DEBUG: Authorization result for '{email}': {result}")
    
    return result


async def is_authorized_user_async(email: str) -> bool:
    """Async version of is_authorized_user - check if email is in authorized list"""
    return is_authorized_user(email)


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> dict:
    """Get current authenticated user from JWT token (from header or cookie)"""
    token = None
    
    # First try to get token from Authorization header
    if credentials:
        token = credentials.credentials
    else:
        # If no Authorization header, try to get from cookie
        token = request.cookies.get("access_token")
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = verify_token(token)
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


def get_login_url(request: Request) -> str:
    """Get Google OAuth login URL"""
    # This function is deprecated - OAuth login URLs should be generated
    # dynamically by the routes that handle OAuth
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
        "iat": datetime.utcnow().timestamp(),
    }


def get_user_info(request: Request) -> dict:
    """Get user info from session or return None if not authenticated"""
    try:
        # Try to get token from cookie
        token = request.cookies.get("access_token")
        if not token:
            return None
            
        # Verify and decode token
        payload = verify_token(token)
        email = payload.get("sub")
        
        if not email or not is_authorized_user(email):
            return None
            
        return payload
    except Exception:
        return None
