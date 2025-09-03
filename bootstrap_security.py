#!/usr/bin/env python3
"""
Bootstrap Security Model for OAuth Configuration

This module implements a progressive security model:
1. If no Google account is linked to the system, allow unauthenticated access to OAuth setup
2. Once a Google account is linked, require authentication for all OAuth changes

This allows initial bootstrap setup while maintaining security after configuration.
"""

import logging
from typing import Optional, Dict, Any
from fastapi import Request, HTTPException, Depends
from auth import get_current_user, is_authorized_user
from database import database

logger = logging.getLogger(__name__)


class BootstrapSecurityError(Exception):
    """Custom exception for bootstrap security errors"""
    pass


async def check_system_bootstrap_status() -> Dict[str, Any]:
    """
    Check if the system is in bootstrap mode (no admin users configured)
    
    Returns:
        Dict with bootstrap status and admin user count
    """
    try:
        admin_count = 0
        oauth_app_count = 0
        
        # Check if oauth_system_settings table exists and has admin config
        try:
            query = """
                SELECT COUNT(*) as admin_count
                FROM oauth_system_settings 
                WHERE setting_key = 'configured_admin_emails'
                AND setting_value IS NOT NULL 
                AND setting_value != ''
            """
            result = await database.fetch_one(query)
            admin_count = result['admin_count'] if result else 0
        except Exception as e:
            if "does not exist" in str(e):
                logger.info("oauth_system_settings table doesn't exist - assuming bootstrap mode")
                admin_count = 0
            else:
                raise e
        
        # Check if there are any active LinkedIn OAuth apps configured
        try:
            oauth_query = """
                SELECT COUNT(*) as oauth_app_count
                FROM linkedin_oauth_config 
                WHERE is_active = true
            """
            oauth_result = await database.fetch_one(oauth_query)
            oauth_app_count = oauth_result['oauth_app_count'] if oauth_result else 0
        except Exception as e:
            if "does not exist" in str(e):
                logger.info("linkedin_oauth_config table doesn't exist - assuming bootstrap mode")
                oauth_app_count = 0
            else:
                logger.warning(f"Error checking LinkedIn OAuth config: {e}")
                oauth_app_count = 0
        
        # System is in bootstrap mode if no admin emails or OAuth apps configured
        is_bootstrap = admin_count == 0 and oauth_app_count == 0
        
        return {
            "is_bootstrap": is_bootstrap,
            "admin_count": admin_count,
            "oauth_app_count": oauth_app_count,
            "status": "bootstrap" if is_bootstrap else "configured"
        }
        
    except Exception as e:
        logger.error(f"Error checking bootstrap status: {e}")
        # If we can't check due to missing tables, assume bootstrap mode for safety
        return {
            "is_bootstrap": True,
            "admin_count": 0,
            "oauth_app_count": 0,
            "status": "bootstrap",
            "note": "Assuming bootstrap mode due to missing tables"
        }


async def require_bootstrap_or_admin_auth(request: Request) -> Optional[Dict[str, Any]]:
    """
    Security dependency that allows unauthenticated access during bootstrap,
    but requires admin authentication once the system is configured.
    
    Returns:
        None during bootstrap mode, or admin user dict after bootstrap
    """
    try:
        # Check if system is in bootstrap mode
        bootstrap_status = await check_system_bootstrap_status()
        
        if bootstrap_status["is_bootstrap"]:
            logger.info("System in bootstrap mode - allowing unauthenticated access")
            return None  # No authentication required during bootstrap
        
        # System is configured, require admin authentication
        logger.info("System configured - requiring admin authentication")
        
        # Try to get current user from various auth methods
        user = None
        try:
            # Try cookie-based auth first (most common for admin)
            from cookie_auth import get_admin_from_cookie
            user = await get_admin_from_cookie(request)
        except ImportError:
            logger.warning("Cookie auth not available")
        except Exception as e:
            logger.debug(f"Cookie auth failed: {e}")
        
        if not user:
            try:
                # Try JWT token auth as fallback
                user = await get_current_user(request)
            except Exception as e:
                logger.debug(f"JWT auth failed: {e}")
        
        if not user:
            raise HTTPException(
                status_code=401,
                detail={
                    "error": "Authentication required",
                    "message": "System is configured - admin authentication required for OAuth management",
                    "bootstrap_status": bootstrap_status
                }
            )
        
        # Verify user is authorized
        if not is_authorized_user(user.get('email', '')):
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "Access denied",
                    "message": "Insufficient privileges for OAuth management",
                    "user_email": user.get('email', 'unknown')
                }
            )
        
        logger.info(f"Admin authenticated: {user.get('email', 'unknown')}")
        return user
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        logger.error(f"Bootstrap security check failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Security check failed",
                "message": "Unable to verify authentication requirements"
            }
        )


async def mark_system_configured(admin_email: str) -> bool:
    """
    Mark the system as configured with an admin user.
    This transitions the system out of bootstrap mode.
    
    Args:
        admin_email: Email of the first admin user
        
    Returns:
        True if successfully marked, False otherwise
    """
    try:
        # Insert or update the configured admin emails setting
        query = """
            INSERT INTO oauth_system_settings 
            (setting_key, setting_value, description, created_by)
            VALUES 
            ('configured_admin_emails', $1, 'List of configured admin email addresses', $2)
            ON CONFLICT (setting_key) 
            DO UPDATE SET 
                setting_value = CASE 
                    WHEN oauth_system_settings.setting_value LIKE '%' || $1 || '%' 
                    THEN oauth_system_settings.setting_value
                    ELSE oauth_system_settings.setting_value || ',' || $1
                END,
                updated_at = CURRENT_TIMESTAMP
        """
        
        await database.execute(query, admin_email, admin_email)
        logger.info(f"System marked as configured with admin: {admin_email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to mark system as configured: {e}")
        return False


async def get_bootstrap_ui_context(request: Request) -> Dict[str, Any]:
    """
    Get UI context information for bootstrap vs configured mode
    
    Returns:
        Dict with UI context for templates
    """
    try:
        bootstrap_status = await check_system_bootstrap_status()
        
        # Try to get current user if system is configured
        current_user = None
        if not bootstrap_status["is_bootstrap"]:
            try:
                current_user = await require_bootstrap_or_admin_auth(request)
            except HTTPException:
                pass  # User not authenticated, but that's OK for UI context
        
        return {
            "bootstrap": bootstrap_status,
            "user": current_user,
            "show_bootstrap_warning": bootstrap_status["is_bootstrap"],
            "require_auth": not bootstrap_status["is_bootstrap"],
            "auth_status": "bootstrap" if bootstrap_status["is_bootstrap"] else "configured"
        }
        
    except Exception as e:
        logger.error(f"Error getting bootstrap UI context: {e}")
        return {
            "bootstrap": {"is_bootstrap": False, "status": "error"},
            "user": None,
            "show_bootstrap_warning": False,
            "require_auth": True,
            "auth_status": "error",
            "error": str(e)
        }
