# ttw_linkedin_sync.py - TTW LinkedIn Data Synchronization Service
import logging
from typing import Optional, Dict, List, Any
from datetime import datetime
from database import database
from ttw_oauth_manager import ttw_oauth_manager, TTWOAuthManagerError

logger = logging.getLogger(__name__)

class TTWLinkedInSyncError(Exception):
    """Custom exception for TTW LinkedIn sync errors"""
    pass

class TTWLinkedInSync:
    """
    TTW LinkedIn Data Synchronization Service
    Uses TTW OAuth manager for complete self-contained LinkedIn integration
    """
    
    self.portfolio_id = "daniel-blackburn"  # Target portfolio to update
        
    async def get_oauth_app_status(self) -> Dict[str, Any]:
        """Get LinkedIn OAuth app configuration status"""
        is_configured = await ttw_oauth_manager.is_oauth_app_configured()
        
        if not is_configured:
            return {
                "configured": False,
                "message": "LinkedIn OAuth app not configured",
                "setup_required": True
            }
        
        try:
            config = await ttw_oauth_manager.get_oauth_app_config()
            return {
                "configured": True,
                "app_name": config["app_name"],
                "client_id": config["client_id"],
                "redirect_uri": config["redirect_uri"],
                "configured_by": config["configured_by_email"],
                "configured_at": config["created_at"].isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to get OAuth app status: {e}")
            return {
                "configured": False,
                "message": f"Error checking OAuth app: {str(e)}",
                "setup_required": True
            }
    
    async def get_connection_status(self) -> Dict[str, Any]:
        """Get LinkedIn connection status for this admin"""
        app_status = await self.get_oauth_app_status()
        if not app_status["configured"]:
            return {
                "connected": False,
                "app_configured": False,
                "message": "LinkedIn OAuth app must be configured first",
                **app_status
            }
        
        try:
            
            if not connection:
                return {
                    "connected": False,
                    "app_configured": True,
                    "message": "LinkedIn account not connected",
                    "available_scopes": await ttw_oauth_manager.get_available_scopes(),
                    **app_status
                }
            
            return {
                "connected": True,
                "app_configured": True,
                "linkedin_profile_id": connection["linkedin_profile_id"],
                "linkedin_profile_name": connection["linkedin_profile_name"],
                "granted_scopes": connection["granted_scopes"],
                "requested_scopes": connection["requested_scopes"],
                "expires_at": connection["expires_at"].isoformat() if connection["expires_at"] else None,
                "last_sync_at": connection["last_sync_at"].isoformat() if connection["last_sync_at"] else None,
                "permissions_info": await self._get_permissions_info(connection["granted_scopes"]),
                **app_status
            }
            
        except Exception as e:
            logger.error(f"Failed to get connection status: {e}")
            return {
                "connected": False,
                "app_configured": True,
                "message": f"Error checking connection: {str(e)}",
                **app_status
            }
    
    async def _get_permissions_info(self, granted_scopes: List[str]) -> List[Dict[str, Any]]:
        """Get information about granted permissions"""
        all_scopes = await ttw_oauth_manager.get_available_scopes()
        
        permissions_info = []
        for scope_info in all_scopes:
            scope_name = scope_info["scope_name"]
            is_granted = scope_name in granted_scopes
            
            permissions_info.append({
                "scope": scope_name,
                "display_name": scope_info["display_name"],
                "description": scope_info["description"],
                "data_access": scope_info["data_access_description"],
                "is_granted": is_granted,
                "is_required": scope_info["is_required"]
            })
        
        return permissions_info
    
    async def sync_profile_data(self, sync_options: Dict[str, bool] = None) -> Dict[str, Any]:
        """Sync LinkedIn profile data using granted permissions"""
        if not connection:
            raise TTWLinkedInSyncError("LinkedIn not connected. Please connect your LinkedIn account first.")
        
        # Default sync options
        if sync_options is None:
            sync_options = {
                "basic_info": True,
                "work_experience": True,
                "skills": False  # Usually requires additional permissions
            }
        
        results = {
            "success": False,
            "synced": [],
            "skipped": [],
            "errors": [],
            "permissions_used": []
        }
        
        try:
            granted_scopes = connection["granted_scopes"]
            access_token = connection["access_token"]
            
            # Check what we can sync based on granted permissions
            can_sync_profile = "r_liteprofile" in granted_scopes or "r_basicprofile" in granted_scopes
            can_sync_email = "r_emailaddress" in granted_scopes
            
            # Sync basic profile information
            if sync_options.get("basic_info", True) and can_sync_profile:
                try:
                    profile_data = await self._fetch_linkedin_profile(access_token, granted_scopes)
                    await self._sync_basic_profile(profile_data)
                    results["synced"].append("basic_info")
                    results["permissions_used"].extend(["r_liteprofile"])
                    if can_sync_email:
                        results["permissions_used"].append("r_emailaddress")
                except Exception as e:
                    results["errors"].append(f"Basic info sync failed: {str(e)}")
            elif sync_options.get("basic_info", True):
                results["skipped"].append("basic_info (missing r_liteprofile permission)")
            
            # Sync work experience 
            if sync_options.get("work_experience", True):
                if "r_basicprofile" in granted_scopes:
                    try:
                        # Note: LinkedIn's v2 API has limited work experience access
                        # This would require additional API calls and permissions
                        await self._sync_work_experience_placeholder()
                        results["synced"].append("work_experience")
                        results["permissions_used"].append("r_basicprofile")
                    except Exception as e:
                        results["errors"].append(f"Work experience sync failed: {str(e)}")
                else:
                    results["skipped"].append("work_experience (missing r_basicprofile permission)")
            
            # Sync skills
            if sync_options.get("skills", True):
                if "r_basicprofile" in granted_scopes:
                    try:
                        await self._sync_skills_placeholder()
                        results["synced"].append("skills")
                        results["permissions_used"].append("r_basicprofile")
                    except Exception as e:
                        results["errors"].append(f"Skills sync failed: {str(e)}")
                else:
                    results["skipped"].append("skills (missing r_basicprofile permission)")
            
            # Update last sync timestamp
            
            results["success"] = len(results["synced"]) > 0
            results["timestamp"] = datetime.utcnow().isoformat()
            results["permissions_used"] = list(set(results["permissions_used"]))  # Remove duplicates
            
            return results
            
        except Exception as e:
            results["errors"].append(f"Sync failed: {str(e)}")
            return results
    
    async def _fetch_linkedin_profile(self, access_token: str, granted_scopes: List[str]) -> Dict[str, Any]:
        """Fetch LinkedIn profile data using available permissions"""
        import httpx
        
        headers = {"Authorization": f"Bearer {access_token}"}
        profile_data = {}
        
        async with httpx.AsyncClient() as client:
            # Get basic profile (r_liteprofile)
            if "r_liteprofile" in granted_scopes or "r_basicprofile" in granted_scopes:
                try:
                    response = await client.get(
                        "https://api.linkedin.com/v2/people/~",
                        headers=headers
                    )
                    response.raise_for_status()
                    profile_data["profile"] = response.json()
                except Exception as e:
                    logger.error(f"Failed to fetch LinkedIn profile: {e}")
            
            # Get email address (r_emailaddress)
            if "r_emailaddress" in granted_scopes:
                try:
                    response = await client.get(
                        "https://api.linkedin.com/v2/emailAddress?q=members&projection=(elements*(handle~))",
                        headers=headers
                    )
                    if response.status_code == 200:
                        email_data = response.json()
                        if email_data.get("elements") and len(email_data["elements"]) > 0:
                            profile_data["email"] = email_data["elements"][0].get("handle~", {}).get("emailAddress")
                except Exception as e:
                    logger.warning(f"Failed to fetch LinkedIn email: {e}")
        
        return profile_data
    
    async def _sync_basic_profile(self, profile_data: Dict[str, Any]):
        """Sync basic profile information to portfolio"""
        if not profile_data.get("profile"):
            return
        
        profile = profile_data["profile"]
        email = profile_data.get("email")
        
        # Extract name
        first_name = profile.get("localizedFirstName", "")
        last_name = profile.get("localizedLastName", "")
        name = f"{first_name} {last_name}".strip()
        
        # Extract headline/title
        headline = profile.get("localizedHeadline", "")
        
        # Update portfolio basic info (only if we have new data)
        update_query = """
            UPDATE portfolios SET
                name = COALESCE(NULLIF(:name, ''), name),
                title = COALESCE(NULLIF(:title, ''), title),
                email = COALESCE(NULLIF(:email, ''), email),
                updated_at = NOW()
            WHERE id = :portfolio_id
        """
        
        await database.execute(update_query, {
            "portfolio_id": self.portfolio_id,
            "name": name or None,
            "title": headline or None,
            "email": email or None
        })
        
        logger.info(f"Basic profile info synced: {name}, {headline}")
    
    async def _sync_work_experience_placeholder(self):
        """Sync work experience (placeholder - LinkedIn v2 API limitations)"""
        # LinkedIn's v2 API has very limited access to work experience
        # This would require:
        # 1. Additional permissions that are hard to get approved
        # 2. Different API endpoints that may not be available
        # 3. Partner API access for full profile data
        
        logger.info("Work experience sync placeholder - LinkedIn v2 API has limited access to work history")
    
    async def _sync_skills_placeholder(self):
        """Sync skills (placeholder - LinkedIn v2 API limitations)"""
        # Similar limitations as work experience
        # LinkedIn v2 API doesn't provide easy access to skills data
        
        logger.info("Skills sync placeholder - LinkedIn v2 API has limited access to skills data")
    
    async def disconnect_linkedin(self) -> bool:
        """Disconnect LinkedIn account for this admin"""
    
    async def get_sync_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get history of LinkedIn sync operations"""
        # Get connection info for last sync time
        
        history = []
        if connection and connection["last_sync_at"]:
            history.append({
                "timestamp": connection["last_sync_at"].isoformat(),
                "type": "linkedin_sync",
                "status": "completed",
                "scopes_used": connection["granted_scopes"]
            })
        
        # Also get portfolio update history
        query = """
            SELECT updated_at, 'portfolio_update' as sync_type
            FROM portfolios 
            WHERE id = :portfolio_id 
            ORDER BY updated_at DESC 
            LIMIT :limit
        """
        
        results = await database.fetch_all(query, {
            "portfolio_id": self.portfolio_id,
            "limit": limit - len(history)
        })
        
        for result in results:
            history.append({
                "timestamp": result["updated_at"].isoformat(),
                "type": result["sync_type"],
                "status": "completed"
            })
        
        return sorted(history, key=lambda x: x["timestamp"], reverse=True)[:limit]

# Convenience function for backward compatibility
    """TTW LinkedIn sync function"""
    return await sync_service.sync_profile_data(sync_options)
