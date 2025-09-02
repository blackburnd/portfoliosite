# linkedin_sync.py - LinkedIn Profile Data Synchronization Module
import os
import json
import logging
from typing import Optional, Dict, List, Any
from linkedin_api import Linkedin
from datetime import datetime
import asyncio
from database import database

logger = logging.getLogger(__name__)

class LinkedInSyncError(Exception):
    """Custom exception for LinkedIn sync errors"""
    pass

class LinkedInSync:
    """
    LinkedIn Profile Data Synchronization Service
    Fetches profile data from LinkedIn and syncs to portfolio database
    """
    
    def __init__(self):
        self.linkedin_username = os.getenv("LINKEDIN_USERNAME")
        self.linkedin_password = os.getenv("LINKEDIN_PASSWORD")
        self.target_profile_id = os.getenv("LINKEDIN_PROFILE_ID", "blackburnd")
        self.portfolio_id = "daniel-blackburn"  # Target portfolio to update
        
    def _get_linkedin_client(self) -> Linkedin:
        """Create authenticated LinkedIn API client"""
        if not self.linkedin_username or not self.linkedin_password:
            raise LinkedInSyncError(
                "LinkedIn credentials not configured. Set LINKEDIN_USERNAME and LINKEDIN_PASSWORD environment variables."
            )
        
        try:
            logger.info(f"Authenticating LinkedIn client for user: {self.linkedin_username}")
            client = Linkedin(self.linkedin_username, self.linkedin_password)
            return client
        except Exception as e:
            logger.error(f"Failed to authenticate LinkedIn client: {str(e)}")
            raise LinkedInSyncError(f"LinkedIn authentication failed: {str(e)}")
    
    def fetch_profile_data(self) -> Dict[str, Any]:
        """Fetch profile data from LinkedIn"""
        try:
            logger.info(f"Fetching LinkedIn profile data for: {self.target_profile_id}")
            client = self._get_linkedin_client()
            
            # Get profile information
            profile = client.get_profile(self.target_profile_id)
            logger.info(f"Successfully fetched profile data for: {profile.get('firstName', 'Unknown')} {profile.get('lastName', 'Unknown')}")
            
            return profile
            
        except Exception as e:
            logger.error(f"Failed to fetch LinkedIn profile data: {str(e)}")
            raise LinkedInSyncError(f"Failed to fetch profile data: {str(e)}")
    
    def fetch_experience_data(self) -> List[Dict[str, Any]]:
        """Fetch work experience data from LinkedIn"""
        try:
            logger.info(f"Fetching LinkedIn experience data for: {self.target_profile_id}")
            client = self._get_linkedin_client()
            
            # Get experience information
            experiences = client.get_profile_experiences(self.target_profile_id)
            logger.info(f"Successfully fetched {len(experiences)} work experiences")
            
            return experiences
            
        except Exception as e:
            logger.error(f"Failed to fetch LinkedIn experience data: {str(e)}")
            raise LinkedInSyncError(f"Failed to fetch experience data: {str(e)}")
    
    def _map_profile_data(self, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        """Map LinkedIn profile data to portfolio schema"""
        mapped_data = {
            "name": f"{profile_data.get('firstName', '')} {profile_data.get('lastName', '')}".strip(),
            "title": profile_data.get('headline', ''),
            "bio": profile_data.get('summary', ''),
            "tagline": profile_data.get('headline', ''),
            "location": None  # LinkedIn API may not provide this in basic profile
        }
        
        # Extract location if available
        if 'locationName' in profile_data:
            mapped_data["location"] = profile_data['locationName']
        
        logger.info(f"Mapped profile data: {mapped_data['name']}, {mapped_data['title']}")
        return mapped_data
    
    def _map_experience_data(self, experiences: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Map LinkedIn experience data to work_experience schema"""
        mapped_experiences = []
        
        for idx, exp in enumerate(experiences):
            # Extract dates
            start_date = None
            end_date = None
            is_current = False
            
            if 'timePeriod' in exp:
                time_period = exp['timePeriod']
                
                # Start date
                if 'startDate' in time_period:
                    start_date_obj = time_period['startDate']
                    year = start_date_obj.get('year')
                    month = start_date_obj.get('month', 1)
                    start_date = f"{year}-{month:02d}" if year else None
                
                # End date
                if 'endDate' in time_period:
                    end_date_obj = time_period['endDate']
                    year = end_date_obj.get('year')
                    month = end_date_obj.get('month', 12)
                    end_date = f"{year}-{month:02d}" if year else None
                else:
                    is_current = True  # No end date means current position
            
            # Extract location
            location = None
            if 'locationName' in exp:
                location = exp['locationName']
            
            mapped_exp = {
                "portfolio_id": self.portfolio_id,
                "company": exp.get('companyName', ''),
                "position": exp.get('title', ''),
                "location": location,
                "start_date": start_date or '',
                "end_date": end_date,
                "description": exp.get('description', ''),
                "is_current": is_current,
                "company_url": exp.get('companyUrn'),  # May need processing
                "sort_order": idx + 1
            }
            
            mapped_experiences.append(mapped_exp)
            logger.info(f"Mapped experience: {mapped_exp['company']} - {mapped_exp['position']}")
        
        return mapped_experiences
    
    async def sync_profile_data(self) -> Dict[str, Any]:
        """Sync LinkedIn profile data to portfolio database"""
        try:
            logger.info("Starting LinkedIn profile data sync")
            
            # Fetch data from LinkedIn
            profile_data = self.fetch_profile_data()
            mapped_profile = self._map_profile_data(profile_data)
            
            # Update portfolio table
            update_query = """
                UPDATE portfolios SET 
                    name = :name,
                    title = :title,
                    bio = :bio,
                    tagline = :tagline,
                    updated_at = NOW()
                WHERE id = :portfolio_id
                RETURNING *
            """
            
            values = {
                "name": mapped_profile["name"],
                "title": mapped_profile["title"], 
                "bio": mapped_profile["bio"],
                "tagline": mapped_profile["tagline"],
                "portfolio_id": self.portfolio_id
            }
            
            updated_portfolio = await database.fetch_one(update_query, values)
            
            if not updated_portfolio:
                raise LinkedInSyncError(f"Portfolio with id '{self.portfolio_id}' not found")
            
            logger.info("Successfully synced LinkedIn profile data")
            return {
                "status": "success",
                "updated_fields": ["name", "title", "bio", "tagline"],
                "profile_data": dict(updated_portfolio)
            }
            
        except Exception as e:
            logger.error(f"Failed to sync LinkedIn profile data: {str(e)}")
            raise LinkedInSyncError(f"Profile sync failed: {str(e)}")
    
    async def sync_experience_data(self) -> Dict[str, Any]:
        """Sync LinkedIn experience data to work_experience database"""
        try:
            logger.info("Starting LinkedIn experience data sync")
            
            # Fetch data from LinkedIn
            experiences = self.fetch_experience_data()
            mapped_experiences = self._map_experience_data(experiences)
            
            # Clear existing work experience for this portfolio (to avoid duplicates)
            delete_query = "DELETE FROM work_experience WHERE portfolio_id = :portfolio_id"
            await database.execute(delete_query, {"portfolio_id": self.portfolio_id})
            logger.info(f"Cleared existing work experience for portfolio: {self.portfolio_id}")
            
            # Insert new work experiences
            created_experiences = []
            for exp in mapped_experiences:
                insert_query = """
                    INSERT INTO work_experience 
                    (portfolio_id, company, position, location, start_date, end_date, 
                     description, is_current, company_url, sort_order)
                    VALUES (:portfolio_id, :company, :position, :location, :start_date, 
                            :end_date, :description, :is_current, :company_url, :sort_order)
                    RETURNING *
                """
                
                created_exp = await database.fetch_one(insert_query, exp)
                created_experiences.append(dict(created_exp))
            
            logger.info(f"Successfully synced {len(created_experiences)} work experiences")
            return {
                "status": "success",
                "experiences_count": len(created_experiences),
                "experiences": created_experiences
            }
            
        except Exception as e:
            logger.error(f"Failed to sync LinkedIn experience data: {str(e)}")
            raise LinkedInSyncError(f"Experience sync failed: {str(e)}")
    
    async def full_sync(self) -> Dict[str, Any]:
        """Perform full sync of both profile and experience data"""
        logger.info("Starting full LinkedIn data sync")
        
        results = {
            "status": "success",
            "sync_timestamp": datetime.utcnow().isoformat(),
            "profile_sync": None,
            "experience_sync": None,
            "errors": []
        }
        
        # Sync profile data
        try:
            results["profile_sync"] = await self.sync_profile_data()
        except Exception as e:
            error_msg = f"Profile sync error: {str(e)}"
            logger.error(error_msg)
            results["errors"].append(error_msg)
            results["status"] = "partial_failure"
        
        # Sync experience data
        try:
            results["experience_sync"] = await self.sync_experience_data()
        except Exception as e:
            error_msg = f"Experience sync error: {str(e)}"
            logger.error(error_msg)
            results["errors"].append(error_msg)
            results["status"] = "partial_failure" if results["status"] == "success" else "failure"
        
        logger.info(f"Full LinkedIn sync completed with status: {results['status']}")
        return results
    
    def get_sync_status(self) -> Dict[str, Any]:
        """Get current sync configuration status"""
        return {
            "linkedin_configured": bool(self.linkedin_username and self.linkedin_password),
            "linkedin_username": self.linkedin_username if self.linkedin_username else None,
            "target_profile_id": self.target_profile_id,
            "portfolio_id": self.portfolio_id
        }

# Create global instance
linkedin_sync = LinkedInSync()