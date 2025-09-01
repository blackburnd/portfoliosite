# cookie_auth.py - Cookie-based authentication for web interface
from fastapi import Request, HTTPException, status, Depends
from auth import verify_token, is_authorized_user


async def get_current_user_from_cookie(request: Request) -> dict:
    """Get current user from cookie-stored JWT token"""
    # Try to get token from cookie
    auth_cookie = request.cookies.get("access_token")
    if not auth_cookie:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please login.",
        )
    
    # Extract token from "Bearer " prefix
    if auth_cookie.startswith("Bearer "):
        token = auth_cookie[7:]
    else:
        token = auth_cookie
    
    try:
        payload = verify_token(token)
        email = payload.get("sub")
        
        if not email or not is_authorized_user(email):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. User not authorized."
            )
        
        return payload
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials. Please login again.",
        )


async def require_admin_auth_cookie(user: dict = Depends(get_current_user_from_cookie)) -> dict:
    """Require admin authentication via cookie for web interface"""
    return user
