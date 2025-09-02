# cookie_auth.py - Cookie-based authentication for web interface
import logging
from fastapi import Request, HTTPException, status, Depends
from auth import verify_token, is_authorized_user

logger = logging.getLogger(__name__)


async def get_current_user_from_cookie(request: Request) -> dict:
    """Get current user from cookie-stored JWT token"""
    logger.info("=== Cookie Authentication Debug ===")
    
    # Try to get token from cookie
    auth_cookie = request.cookies.get("access_token")
    logger.info(f"Auth cookie present: {bool(auth_cookie)}")
    
    if not auth_cookie:
        logger.warning("No access_token cookie found")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please login.",
        )
    
    # Extract token from "Bearer " prefix
    if auth_cookie.startswith("Bearer "):
        token = auth_cookie[7:]
        logger.info("Extracted token from Bearer prefix")
    else:
        token = auth_cookie
        logger.info("Using cookie value directly as token")
    
    logger.info(f"Token length: {len(token) if token else 0}")
    
    try:
        payload = verify_token(token)
        email = payload.get("sub")
        logger.info(f"Token verified successfully for email: {email}")
        
        if not email or not is_authorized_user(email):
            logger.warning(f"User not authorized: {email}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. User not authorized."
            )
        
        logger.info("Authentication successful")
        return payload
    except Exception as e:
        logger.error(f"Token verification failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials. Please login again.",
        )


async def require_admin_auth_cookie(user: dict = Depends(get_current_user_from_cookie)) -> dict:
    """Require admin authentication via cookie for web interface"""
    return user
