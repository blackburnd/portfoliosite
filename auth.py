# auth.py - Google OAuth Authentication Module
import os
from typing import Optional
from datetime import datetime, timedelta
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
import secrets

from oauth_client import oauth

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480  # 8 hours

# Authorized emails - load from environment as fallback
AUTHORIZED_EMAILS = os.getenv("AUTHORIZED_EMAILS", "").split(",")
AUTHORIZED_EMAILS = [
    email.strip() for email in AUTHORIZED_EMAILS if email.strip()
]


async def configure_oauth_from_database():
    """Configure OAuth from database settings"""
    try:
        from ttw_oauth_manager import TTWOAuthManager

        ttw_manager = TTWOAuthManager()
        google_config = await ttw_manager.get_google_oauth_app_config()

        if google_config:
            oauth.register(
                name='google',
                client_id=google_config['client_id'],
                client_secret=google_config.get('client_secret'),
                server_metadata_url=(
                    'https://accounts.google.com/.well-known/openid-configuration'
                ),
                client_kwargs={
                    'scope': 'openid email profile'
                }
            )
            client_id = google_config['client_id'][:10]
            print(
                "✅ OAuth configured from database with client ID: "
                f"{client_id}..."
            )
            return True
        else:
            print("❌ No Google OAuth configuration found in database")
            return False

    except Exception as e:
        print(f"❌ Failed to configure OAuth from database: {e}")
        return False

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
    """Check if email is in authorized list"""
    return email in AUTHORIZED_EMAILS


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> dict:
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


async def get_auth_status():
    """Get authentication configuration status"""
    # Try to configure OAuth if not already done
    is_configured = (
        hasattr(oauth, 'google') and oauth.google.client_id is not None
    )
    if not is_configured:
        await configure_oauth_from_database()
        is_configured = (
            hasattr(oauth, 'google') and oauth.google.client_id is not None
        )

    return {
        "google_oauth_configured": is_configured,
        "authorized_emails_count": len(AUTHORIZED_EMAILS)
    }
