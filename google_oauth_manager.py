"""
Google OAuth Token Management Module
Simple display of Google OAuth tokens from the database
"""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from auth import require_admin_auth_session
from database import database

# Create router for Google OAuth management
router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/admin/google/oauth/tokens", response_class=HTMLResponse)
async def view_google_oauth_tokens(request: Request, admin: dict = Depends(require_admin_auth_session)):
    """Display Google OAuth tokens table"""
    try:
        query = """
        SELECT 
            id,
            admin_email,
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
