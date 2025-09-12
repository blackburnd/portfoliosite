# auth.py - Google OAuth Authentication Module
import os
from typing import Optional
from datetime import datetime, timedelta
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
import secrets


# Configuration
SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480  # 8 hours

# Authorized emails - load from environment as fallback
AUTHORIZED_EMAILS = os.getenv("AUTHORIZED_EMAILS", "").split(",")
AUTHORIZED_EMAILS = [
    email.strip() for email in AUTHORIZED_EMAILS if email.strip()
]


# Security bearer for JWT tokens
security = HTTPBearer(auto_error=False)


class AuthenticationError(Exception):
    """Custom authentication error"""
    pass


def create_access_token(
    data: dict, expires_delta: Optional[timedelta] = None
):
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
        expire = datetime.utcnow() + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({"exp": expire})
    logger.info(f"Token payload: {to_encode}")

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    logger.info(
        "Created JWT token (first 50 chars): "
        f"{encoded_jwt[:50] if encoded_jwt else 'None'}"
    )
    return encoded_jwt


def verify_token(token: str) -> dict:
    """Verify and decode JWT token"""
    import logging
    logger = logging.getLogger(__name__)

    logger.info("=== Token Verification Debug ===")
    logger.info(f"SECRET_KEY configured: {bool(SECRET_KEY)}")
    logger.info(f"SECRET_KEY length: {len(SECRET_KEY) if SECRET_KEY else 0}")
    logger.info(
        f"Token to verify (first 50 chars): {token[:50] if token else 'None'}"
    )

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
    """Check if email is in authorized list (sync version using env var)"""
    return email in AUTHORIZED_EMAILS


async def is_authorized_user_async(email: str) -> bool:
    """Check if email is in authorized list (async version using database)"""
    try:
        from app.routers.site_config import SiteConfigManager
        import os
        
        config_manager = SiteConfigManager()
        authorized_emails_str = await config_manager.get_config(
            "authorized_emails"
        )
        
        # Fall back to environment variable if not in database
        if not authorized_emails_str:
            authorized_emails_str = os.getenv("AUTHORIZED_EMAILS", "")
        
        if not authorized_emails_str:
            return False
            
        authorized_emails = [
            e.strip() for e in authorized_emails_str.split(",")
            if e.strip()
        ]
        
        return email in authorized_emails
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error checking authorized user: {e}")
        # Fall back to sync version on error
        return email in AUTHORIZED_EMAILS


async def require_admin_auth(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> dict:
    """Dependency to require admin authentication using database config"""
    user_info = await get_current_user(request, credentials)
    email = user_info.get("sub")  # JWT payload uses 'sub' not 'email'
    
    if not email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not found in token"
        )
    
    if not await is_authorized_user_async(email):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied - not an authorized admin"
        )
    
    return user_info


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
