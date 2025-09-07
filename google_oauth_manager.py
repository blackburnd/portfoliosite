"""
Google OAuth Token Management Module
Handles display and management of Google OAuth tokens stored in the database
"""

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import psycopg2
from datetime import datetime, timezone
from typing import List, Dict
import os
from auth import require_admin_auth_session
from log_capture import add_log

# Create router for Google OAuth management
router = APIRouter()
templates = Jinja2Templates(directory="templates")


def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        database=os.getenv("DB_NAME", "portfolio"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "password")
    )

def get_google_oauth_tokens() -> List[Dict]:
    """Retrieve all Google OAuth tokens from database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = """
        SELECT 
            id,
            admin_email,
            CASE 
                WHEN access_token IS NOT NULL THEN '[ENCRYPTED]' 
                ELSE NULL 
            END as access_token_status,
            CASE 
                WHEN refresh_token IS NOT NULL THEN '[ENCRYPTED]' 
                ELSE NULL 
            END as refresh_token_status,
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
        
        cursor.execute(query)
        rows = cursor.fetchall()
        
        tokens = []
        for row in rows:
            token_data = {
                'id': str(row[0]),
                'admin_email': row[1],
                'access_token_status': row[2],
                'refresh_token_status': row[3],
                'token_expires_at': row[4],
                'granted_scopes': row[5].split(' ') if row[5] else [],
                'requested_scopes': row[6].split(' ') if row[6] else [],
                'token_type': row[7],
                'last_used_at': row[8],
                'is_active': row[9],
                'created_at': row[10],
                'updated_at': row[11],
                'is_expired': row[4] < datetime.now(timezone.utc) if row[4] else False
            }
            tokens.append(token_data)
        
        cursor.close()
        conn.close()
        
        add_log("INFO", "google_oauth_tokens_retrieved", f"Retrieved {len(tokens)} Google OAuth token records")
        return tokens
        
    except Exception as e:
        add_log("ERROR", "google_oauth_tokens_retrieval_error", f"Error retrieving Google OAuth tokens: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

def revoke_google_oauth_token(admin_email: str) -> bool:
    """Mark a Google OAuth token as inactive"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = """
        UPDATE google_oauth_tokens 
        SET is_active = FALSE, updated_at = NOW()
        WHERE admin_email = %s
        """
        
        cursor.execute(query, (admin_email,))
        affected_rows = cursor.rowcount
        conn.commit()
        
        cursor.close()
        conn.close()
        
        if affected_rows > 0:
            add_log("INFO", "google_oauth_token_revoked", f"Revoked Google OAuth token for {admin_email}")
            return True
        else:
            add_log("WARNING", "google_oauth_token_not_found", f"No active Google OAuth token found for {admin_email}")
            return False
            
    except Exception as e:
        add_log("ERROR", "google_oauth_token_revoke_error", f"Error revoking Google OAuth token for {admin_email}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/admin/google/oauth/tokens", response_class=HTMLResponse)
async def view_google_oauth_tokens(request: Request, admin: dict = Depends(require_admin_auth_session)):
    """Display Google OAuth tokens management page"""
    admin_email = admin.get("email")
    add_log("INFO", "admin_google_oauth_tokens_view", f"Admin {admin_email} viewing Google OAuth tokens")
    
    try:
        tokens = get_google_oauth_tokens()
        
        # Calculate summary statistics
        total_tokens = len(tokens)
        active_tokens = len([t for t in tokens if t['is_active']])
        expired_tokens = len([t for t in tokens if t['is_expired']])
        gmail_enabled_tokens = len([t for t in tokens if 'https://www.googleapis.com/auth/gmail.send' in t['granted_scopes']])
        
        stats = {
            'total_tokens': total_tokens,
            'active_tokens': active_tokens,
            'expired_tokens': expired_tokens,
            'gmail_enabled_tokens': gmail_enabled_tokens
        }
        
        return templates.TemplateResponse("google_oauth_tokens.html", {
            "request": request,
            "tokens": tokens,
            "stats": stats,
            "admin": admin
        })
        
    except Exception as e:
        add_log("ERROR", "admin_google_oauth_tokens_view_error", f"Error displaying Google OAuth tokens for admin {admin_email}: {str(e)}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error_message": f"Error loading Google OAuth tokens: {str(e)}",
            "admin": admin
        })

@router.post("/admin/google/oauth/tokens/revoke/{admin_email}")
async def revoke_token(request: Request, admin_email: str, admin: dict = Depends(require_admin_auth_session)):
    """Revoke a Google OAuth token"""
    current_admin_email = admin.get("email")
    add_log("INFO", "admin_google_oauth_token_revoke", f"Admin {current_admin_email} revoking token for {admin_email}")
    
    try:
        success = revoke_google_oauth_token(admin_email)
        
        if success:
            return {"status": "success", "message": f"Token revoked for {admin_email}"}
        else:
            return {"status": "error", "message": f"No active token found for {admin_email}"}
            
    except Exception as e:
        add_log("ERROR", "admin_google_oauth_token_revoke_error", f"Error revoking token for {admin_email}: {str(e)}")
        return {"status": "error", "message": f"Error revoking token: {str(e)}"}
