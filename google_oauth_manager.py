"""
Google OAuth Token Management Module
Simple display of Google OAuth tokens from the database
"""

import os
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from database import database
from ttw_oauth_manager import TTWOAuthManager
from log_capture import add_log

# Create router for Google OAuth management
router = APIRouter()
templates = Jinja2Templates(directory="templates")


async def require_admin_auth_session(request: Request):
    """Require admin authentication via session with fallback for OAuth testing"""
    try:
        # Check for emergency admin bypass (when OAuth is broken during testing)
        admin_bypass_token = request.headers.get("X-Admin-Bypass-Token")
        emergency_password = os.getenv("ADMIN_EMERGENCY_PASSWORD")
        
        if admin_bypass_token and emergency_password and admin_bypass_token == emergency_password:
            add_log("WARNING", "Admin bypass token used - OAuth testing mode", "admin_auth_bypass")
            return {
                "email": "admin@blackburnsystems.com",
                "authenticated": True,
                "is_admin": True,
                "bypass_mode": True
            }
        
        # Check if OAuth is broken/not configured and allow admin access for configuration
        try:
            ttw_manager = TTWOAuthManager()
            oauth_configured = await ttw_manager.is_google_oauth_app_configured()
            
            # If OAuth is not configured, allow admin access to set it up
            if not oauth_configured:
                add_log("INFO", "OAuth not configured - granting admin access for setup", "admin_auth_oauth_fallback")
                return {
                    "email": "admin@blackburnsystems.com", 
                    "authenticated": True,
                    "is_admin": True,
                    "oauth_fallback": True
                }
        except Exception as oauth_check_error:
            # If we can't even check OAuth status, something is broken - allow admin access
            add_log("WARNING", f"OAuth configuration check failed - granting admin access: {str(oauth_check_error)}", "admin_auth_oauth_error_fallback")
            return {
                "email": "admin@blackburnsystems.com",
                "authenticated": True, 
                "is_admin": True,
                "oauth_error_fallback": True
            }
        
        # Standard session-based authentication
        if not hasattr(request, 'session') or 'user' not in request.session:
            client_host = request.client.host if request.client else 'unknown'
            add_log("WARNING", f"Request from {client_host} missing session or user", "admin_auth_no_session")
            raise HTTPException(
                status_code=401,
                detail="Authentication required. Please log in."
            )
        
        user_session = request.session.get('user', {})
        if (not user_session.get('authenticated') or
                not user_session.get('is_admin')):
            user_email = user_session.get('email', 'unknown')
            add_log("WARNING", f"User {user_email} attempted admin access", "admin_auth_insufficient_privileges")
            raise HTTPException(
                status_code=403,
                detail="Admin access required."
            )
        
        return user_session
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        add_log("ERROR", f"Unexpected error in admin auth: {str(e)}", "admin_auth_exception")
        raise HTTPException(
            status_code=500,
            detail="Authentication error occurred."
        )


@router.get("/admin/google/oauth/tokens", response_class=HTMLResponse)
async def view_google_oauth_tokens(request: Request):
    """Display Google OAuth tokens table"""
    try:
        query = """
        SELECT 
            id,
            portfolio_id,
            access_token,
            refresh_token,
            token_expires_at,
            granted_scopes,
            requested_scopes,
            token_type,
            last_used_at,
            is_active,
            created_at,
            updated_at
        FROM google_oauth_tokens 
        ORDER BY created_at DESC
        """
        
        rows = await database.fetch_all(query)
        
        return templates.TemplateResponse("google_oauth_tokens_simple.html", {
            "request": request,
            "tokens": rows,
            "admin": admin
        })
        
    except Exception as e:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error_message": f"Error loading Google OAuth tokens: {str(e)}",
            "admin": admin
        })
