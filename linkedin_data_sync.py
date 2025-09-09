# linkedin_data_sync.py - Enhanced LinkedIn Data Synchronization Service
import logging
from typing import Optional, Dict, List, Any
from datetime import datetime
import asyncio
from database import database
from ttw_oauth_manager import ttw_oauth_manager, TTWOAuthManagerError

logger = logging.getLogger(__name__)

class LinkedInDataSyncError(Exception):
    """Custom exception for LinkedIn data sync errors"""
    pass

class LinkedInDataSync:
    """
    Enhanced LinkedIn Data Synchronization Service
    Uses OAuth-based authentication to fetch and sync LinkedIn profile data
    """
    
    def __init__(self, admin_email: str):
        self.admin_email = admin_email
        self.portfolio_id = "daniel-blackburn"  # Target portfolio to update
        
    async def is_linkedin_available(self) -> bool:
        """Check if LinkedIn data sync is available for this admin"""
        return await oauth_manager.is_linkedin_connected(self.admin_email)
    
    async def get_linkedin_connection_status(self) -> Dict[str, Any]:
        """Get LinkedIn connection status and basic info"""
        is_connected = await self.is_linkedin_available()
        
        if not is_connected:
            return {
                "connected": False,
                "message": "LinkedIn not connected",
                "auth_url": None
            }
        
        try:
            credentials = await oauth_manager.get_linkedin_credentials(self.admin_email)
            profile_data = await oauth_manager.get_linkedin_profile_data(self.admin_email)
            
            return {
                "connected": True,
                "linkedin_profile_id": credentials.get("linkedin_profile_id"),
                "expires_at": credentials.get("expires_at").isoformat() if credentials.get("expires_at") else None,
                "scope": credentials.get("scope"),
                "profile_name": self._extract_profile_name(profile_data),
                "last_sync": await self._get_last_sync_time()
            }
        except Exception as e:
            logger.error(f"Failed to get LinkedIn connection status: {e}")
            return {
                "connected": False,
                "message": f"Error checking LinkedIn connection: {str(e)}",
                "auth_url": None
            }
    
    def _extract_profile_name(self, profile_data: Optional[Dict]) -> Optional[str]:
        """Extract display name from LinkedIn profile data"""
        if not profile_data or not profile_data.get("profile"):
            return None
        
        profile = profile_data["profile"]
        first_name = profile.get("localizedFirstName", "")
        last_name = profile.get("localizedLastName", "")
        return f"{first_name} {last_name}".strip() or None
    
    async def _get_last_sync_time(self) -> Optional[str]:
        """Get the last time LinkedIn data was synced"""
        query = """
            SELECT updated_at FROM portfolios 
            WHERE id = :portfolio_id AND updated_at > created_at
            ORDER BY updated_at DESC LIMIT 1
        """
        result = await database.fetch_one(query, {"portfolio_id": self.portfolio_id})
        return result["updated_at"].isoformat() if result else None
    
    async def sync_profile_data(self, sync_options: Dict[str, bool] = None) -> Dict[str, Any]:
        """
        Sync LinkedIn profile data to portfolio database
        
        Args:
            sync_options: Dict with keys like 'basic_info', 'work_experience', 'skills'
        """
        if not await self.is_linkedin_available():
            raise LinkedInDataSyncError("LinkedIn not connected. Please authenticate first.")
        
        # Default sync options
        if sync_options is None:
            sync_options = {
                "basic_info": True,
                "work_experience": True,
                "skills": True
            }
        
        results = {
            "success": False,
            "synced": [],
            "skipped": [],
            "errors": []
        }
        
        try:
            # Get LinkedIn profile data
            profile_data = await oauth_manager.get_linkedin_profile_data(self.admin_email)
            if not profile_data:
                raise LinkedInDataSyncError("Failed to fetch LinkedIn profile data")
            
            profile = profile_data["profile"]
            email = profile_data.get("email")
            
            # Sync basic profile information
            if sync_options.get("basic_info", True):
                try:
                    await self._sync_basic_profile(profile, email)
                    results["synced"].append("basic_info")
                except Exception as e:
                    results["errors"].append(f"Basic info sync failed: {str(e)}")
            else:
                results["skipped"].append("basic_info")
            
            # Sync work experience (would need additional LinkedIn API calls)
            if sync_options.get("work_experience", True):
                try:
                    await self._sync_work_experience(profile)
                    results["synced"].append("work_experience")
                except Exception as e:
                    results["errors"].append(f"Work experience sync failed: {str(e)}")
            else:
                results["skipped"].append("work_experience")
            
            # Sync skills (would need additional LinkedIn API calls)
            if sync_options.get("skills", True):
                try:
                    await self._sync_skills(profile)
                    results["synced"].append("skills")
                except Exception as e:
                    results["errors"].append(f"Skills sync failed: {str(e)}")
            else:
                results["skipped"].append("skills")
            
            results["success"] = len(results["synced"]) > 0
            results["timestamp"] = datetime.utcnow().isoformat()
            
            logger.info(f"LinkedIn sync completed for {self.admin_email}: {results}")
            return results
            
        except Exception as e:
            logger.error(f"LinkedIn sync failed for {self.admin_email}: {e}")
            results["errors"].append(f"Sync failed: {str(e)}")
            return results
    
    async def _sync_basic_profile(self, profile: Dict[str, Any], email: Optional[str]):
        """Sync basic profile information"""
        first_name = profile.get("localizedFirstName", "")
        last_name = profile.get("localizedLastName", "")
        name = f"{first_name} {last_name}".strip()
        
        # Extract headline/title
        headline = profile.get("localizedHeadline", "")
        
        # Update portfolio basic info
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
    
    async def _sync_work_experience(self, profile: Dict[str, Any]):
        """Sync work experience (placeholder - would need additional API calls)"""
        # LinkedIn's basic profile API doesn't include work experience
        # Would need to make additional API calls to:
        # https://api.linkedin.com/v2/people/(id)/positions
        # This requires additional permissions and API calls
        
        logger.info("Work experience sync placeholder - would need additional LinkedIn API integration")
    
    async def _sync_skills(self, profile: Dict[str, Any]):
        """Sync skills (placeholder - would need additional API calls)"""
        # LinkedIn's basic profile API doesn't include skills
        # Would need to make additional API calls to:
        # https://api.linkedin.com/v2/people/(id)/skills
        # This requires additional permissions and API calls
        
        logger.info("Skills sync placeholder - would need additional LinkedIn API integration")
    
    async def disconnect_linkedin(self) -> bool:
        """Disconnect LinkedIn account for this admin"""
        try:
            await oauth_manager.remove_linkedin_credentials(self.admin_email)
            logger.info(f"LinkedIn disconnected for admin: {self.admin_email}")
            return True
        except Exception as e:
            logger.error(f"Failed to disconnect LinkedIn for {self.admin_email}: {e}")
            return False
    
    async def get_sync_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get history of LinkedIn sync operations"""
        # This would require a sync_history table to track operations
        # For now, return basic portfolio update history
        query = """
            SELECT updated_at, 'portfolio_update' as sync_type
            FROM portfolios 
            WHERE id = :portfolio_id 
            ORDER BY updated_at DESC 
            LIMIT :limit
        """
        
        results = await database.fetch_all(query, {
            "portfolio_id": self.portfolio_id,
            "limit": limit
        })
        
        return [
            {
                "timestamp": result["updated_at"].isoformat(),
                "type": result["sync_type"],
                "status": "completed"
            }
            for result in results
        ]

# Convenience function for backward compatibility
async def linkedin_sync(admin_email: str, sync_options: Dict[str, bool] = None) -> Dict[str, Any]:
    """
    Backward compatible LinkedIn sync function
    """
    sync_service = LinkedInDataSync(admin_email)
    return await sync_service.sync_profile_data(sync_options)
