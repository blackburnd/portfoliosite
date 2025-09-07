import asyncio
from databases import Database
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import os
import uuid

# Database configuration - check both possible environment variable names
DATABASE_URL = os.getenv("_DATABASE_URL") or os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("No _DATABASE_URL or DATABASE_URL environment variable set")

database = Database(DATABASE_URL)

async def init_database():
    """Initialize database connection"""
    await database.connect()
    print(f"Connected to PostgreSQL database: {DATABASE_URL}")

async def close_database():
    """Close database connection"""
    await database.disconnect()

class PortfolioDatabase:
    @staticmethod
    async def get_portfolio(portfolio_id: str = "daniel-blackburn") -> Optional[Dict[str, Any]]:
        """Get portfolio data with related work experience and projects"""
        
        # Get main portfolio data
        portfolio_query = """
        SELECT id, name, title, bio, tagline, profile_image,
               email, phone, vcard, resume_url, resume_download, 
               github, twitter, skills, created_at, updated_at
        FROM portfolios 
        WHERE id = :portfolio_id
        """
        
        portfolio = await database.fetch_one(portfolio_query, {"portfolio_id": portfolio_id})
        if not portfolio:
            return None
        
        # Get work experience
        work_query = """
        SELECT id, company, position, location, start_date, end_date,
               description, is_current, company_url, sort_order
        FROM work_experience 
        WHERE portfolio_id = :portfolio_id 
        ORDER BY sort_order, start_date DESC
        """
        work_exp = await database.fetch_all(work_query, {"portfolio_id": portfolio_id})
        
        # Get projects
        projects_query = """
        SELECT id, title, description, url, image_url, technologies, sort_order
        FROM projects 
        WHERE portfolio_id = :portfolio_id 
        ORDER BY sort_order, created_at DESC
        """
        projects = await database.fetch_all(projects_query, {"portfolio_id": portfolio_id})
        
        # Format the response
        return {
            "id": portfolio["id"],
            "name": portfolio["name"],
            "title": portfolio["title"],
            "bio": portfolio["bio"],
            "tagline": portfolio["tagline"],
            "profile_image": portfolio["profile_image"],
            "contact": {
                "email": portfolio["email"],
                "phone": portfolio["phone"],
                "vcard": portfolio["vcard"]
            },
            "social_links": {
                "resume": portfolio["resume_url"],
                "resume_download": portfolio["resume_download"],
                "github": portfolio["github"],
                "twitter": portfolio["twitter"]
            },
            "work_experience": [
                {
                    "id": str(work["id"]),
                    "company": work["company"],
                    "position": work["position"],
                    "location": work["location"],
                    "start_date": work["start_date"],
                    "end_date": work["end_date"],
                    "description": work["description"],
                    "is_current": work["is_current"],
                    "company_url": work["company_url"]
                } for work in work_exp
            ],
            "projects": [
                {
                    "id": str(project["id"]),
                    "title": project["title"],
                    "description": project["description"],
                    "url": project["url"],
                    "image_url": project["image_url"],
                    "technologies": project["technologies"]
                } for project in projects
            ],
            "skills": portfolio["skills"],
            "created_at": portfolio["created_at"] if isinstance(portfolio["created_at"], str) else portfolio["created_at"].isoformat(),
            "updated_at": portfolio["updated_at"] if isinstance(portfolio["updated_at"], str) else portfolio["updated_at"].isoformat()
        }
    
    @staticmethod
    async def update_portfolio(portfolio_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update portfolio information"""
        
        # Build dynamic update query
        set_clauses = []
        values = {"portfolio_id": portfolio_id}
        
        for key, value in updates.items():
            if key in ["name", "title", "bio", "tagline", "profile_image"]:
                set_clauses.append(f"{key} = :{key}")
                values[key] = value
        
        if not set_clauses:
            # No valid fields to update, just return current portfolio
            return await PortfolioDatabase.get_portfolio(portfolio_id)
        
        query = f"""
        UPDATE portfolios 
        SET {', '.join(set_clauses)}, updated_at = NOW()
        WHERE id = :portfolio_id
        """
        
        await database.execute(query, values)
        return await PortfolioDatabase.get_portfolio(portfolio_id)
    
    @staticmethod
    async def add_work_experience(portfolio_id: str, work_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add new work experience"""
        
        query = """
        INSERT INTO work_experience 
        (portfolio_id, company, position, location, start_date, end_date, 
         description, is_current, company_url, sort_order)
        VALUES (:portfolio_id, :company, :position, :location, :start_date, 
                :end_date, :description, :is_current, :company_url, :sort_order)
        RETURNING id, company, position, location, start_date, end_date, 
                  description, is_current, company_url
        """
        
        values = {
            "portfolio_id": portfolio_id,
            "company": work_data["company"],
            "position": work_data["position"],
            "location": work_data.get("location"),
            "start_date": work_data["start_date"],
            "end_date": work_data.get("end_date"),
            "description": work_data.get("description"),
            "is_current": work_data.get("is_current", False),
            "company_url": work_data.get("company_url"),
            "sort_order": work_data.get("sort_order", 0)
        }
        
        result = await database.fetch_one(query, values)
        
        return {
            "id": str(result["id"]),
            "company": result["company"],
            "position": result["position"],
            "location": result["location"],
            "start_date": result["start_date"],
            "end_date": result["end_date"],
            "description": result["description"],
            "is_current": result["is_current"],
            "company_url": result["company_url"]
        }
    
    @staticmethod
    async def add_project(portfolio_id: str, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add new project"""
        
        query = """
        INSERT INTO projects 
        (portfolio_id, title, description, url, image_url, technologies, sort_order)
        VALUES (:portfolio_id, :title, :description, :url, :image_url, 
                :technologies, :sort_order)
        RETURNING id, title, description, url, image_url, technologies
        """
        
        values = {
            "portfolio_id": portfolio_id,
            "title": project_data["title"],
            "description": project_data["description"],
            "url": project_data.get("url"),
            "image_url": project_data.get("image_url"),
            "technologies": json.dumps(project_data.get("technologies", [])),
            "sort_order": project_data.get("sort_order", 0)
        }
        
        result = await database.fetch_one(query, values)
        
        return {
            "id": str(result["id"]),
            "title": result["title"],
            "description": result["description"],
            "url": result["url"],
            "image_url": result["image_url"],
            "technologies": result["technologies"]
        }
    
    @staticmethod
    async def save_message(portfolio_id: str, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Save contact message"""
        
        query = """
        INSERT INTO contact_messages 
        (portfolio_id, name, email, subject, message)
        VALUES (:portfolio_id, :name, :email, :subject, :message)
        RETURNING id, name, email, subject, message, created_at, is_read
        """
        
        values = {
            "portfolio_id": portfolio_id,
            "name": message_data["name"],
            "email": message_data["email"],
            "subject": message_data.get("subject"),
            "message": message_data["message"]
        }
        
        result = await database.fetch_one(query, values)
        
        return {
            "id": str(result["id"]),
            "name": result["name"],
            "email": result["email"],
            "subject": result["subject"],
            "message": result["message"],
            "created_at": result["created_at"] if isinstance(result["created_at"], str) else result["created_at"].isoformat(),
            "is_read": result["is_read"]
        }
    
    @staticmethod
    async def get_messages(portfolio_id: str = "daniel-blackburn") -> List[Dict[str, Any]]:
        """Get all contact messages"""
        
        query = """
        SELECT id, name, email, subject, message, created_at, is_read
        FROM contact_messages 
        WHERE portfolio_id = :portfolio_id 
        ORDER BY created_at DESC
        LIMIT 100
        """
        
        results = await database.fetch_all(query, {"portfolio_id": portfolio_id})
        
        return [
            {
                "id": str(row["id"]),
                "name": row["name"],
                "email": row["email"],
                "subject": row["subject"],
                "message": row["message"],
                "created_at": row["created_at"] if isinstance(row["created_at"], str) else row["created_at"].isoformat(),
                "is_read": row["is_read"]
            } for row in results
        ]

# Global database instance
db = PortfolioDatabase()


async def get_database():
    """Get database instance"""
    return db


async def save_google_oauth_tokens(admin_email: str, access_token: str, refresh_token: str, 
                                 expires_at: datetime, granted_scopes: str, requested_scopes: str) -> bool:
    """Save Google OAuth tokens to database"""
    try:
        # First try to update existing record
        update_query = """
        UPDATE google_oauth_tokens 
        SET access_token = :access_token,
            refresh_token = :refresh_token,
            token_expires_at = :expires_at,
            granted_scopes = :granted_scopes,
            requested_scopes = :requested_scopes,
            last_used_at = NOW(),
            updated_at = NOW(),
            is_active = TRUE
        WHERE admin_email = :admin_email
        """
        
        result = await database.execute(update_query, {
            "admin_email": admin_email,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_at": expires_at,
            "granted_scopes": granted_scopes,
            "requested_scopes": requested_scopes
        })
        
        # If no rows were updated, insert new record
        if result == 0:
            insert_query = """
            INSERT INTO google_oauth_tokens 
            (admin_email, access_token, refresh_token, token_expires_at, 
             granted_scopes, requested_scopes, last_used_at)
            VALUES (:admin_email, :access_token, :refresh_token, :expires_at,
                    :granted_scopes, :requested_scopes, NOW())
            """
            
            await database.execute(insert_query, {
                "admin_email": admin_email,
                "access_token": access_token,
                "refresh_token": refresh_token,
                "expires_at": expires_at,
                "granted_scopes": granted_scopes,
                "requested_scopes": requested_scopes
            })
        
        return True
    except Exception as e:
        logger.error(f"Error saving Google OAuth tokens: {e}")
        raise  # Re-raise the exception so calling code can handle it


async def get_google_oauth_tokens(admin_email: str) -> Optional[Dict[str, Any]]:
    """Get Google OAuth tokens for an admin user from database"""
    try:
        query = """
        SELECT access_token, refresh_token, token_expires_at, 
               granted_scopes, requested_scopes, last_used_at
        FROM google_oauth_tokens 
        WHERE admin_email = :admin_email AND is_active = TRUE
        """
        
        result = await database.fetch_one(query, {"admin_email": admin_email})
        
        if result:
            return {
                "access_token": result["access_token"],
                "refresh_token": result["refresh_token"],
                "expires_at": result["token_expires_at"],
                "granted_scopes": result["granted_scopes"],
                "requested_scopes": result["requested_scopes"],
                "last_used_at": result["last_used_at"]
            }
        return None
    except Exception as e:
        print(f"Error getting Google OAuth tokens: {e}")
        return None


async def update_google_oauth_token_usage(admin_email: str) -> bool:
    """Update last_used_at timestamp for Google OAuth tokens"""
    try:
        query = """
        UPDATE google_oauth_tokens 
        SET last_used_at = NOW()
        WHERE admin_email = :admin_email AND is_active = TRUE
        """
        
        await database.execute(query, {"admin_email": admin_email})
        return True
    except Exception as e:
        print(f"Error updating Google OAuth token usage: {e}")
        return False


async def revoke_google_oauth_tokens(admin_email: str) -> bool:
    """Mark Google OAuth tokens as inactive (revoked)"""
    try:
        query = """
        UPDATE google_oauth_tokens 
        SET is_active = FALSE,
            updated_at = NOW()
        WHERE admin_email = :admin_email
        """
        
        await database.execute(query, {"admin_email": admin_email})
        return True
    except Exception as e:
        print(f"Error revoking Google OAuth tokens: {e}")
        return False


async def get_oauth_tokens_for_admin(admin_email: str) -> Optional[Dict[str, str]]:
    """Get OAuth tokens for an admin user from database (legacy function for compatibility)"""
    return await get_google_oauth_tokens(admin_email)
