import asyncio
from databases import Database
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import os
import uuid

# Centralized database configuration - SINGLE SOURCE OF TRUTH
def get_database_url() -> str:
    """Get database URL from environment variables."""
    database_url = os.getenv("_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("No _DATABASE_URL or DATABASE_URL environment variable set")
    return database_url

# Single database instance
database = Database(get_database_url())

# Global portfolio ID - set during startup
PORTFOLIO_ID = None

async def init_database():
    """Initialize database connection and ensure portfolio exists"""
    global PORTFOLIO_ID
    await database.connect()
    
    # Get repo name from environment variable
    repo_name = os.getenv("_REPO_NAME", "default-portfolio")
    print(f"🔍 Looking for portfolio with id: {repo_name}")
    
    try:
        # Check if portfolio exists with id matching repo name
        # Note: 'id' is the string field, 'portfolio_id' is the UUID primary key
        portfolio_query = """SELECT portfolio_id FROM portfolios 
                             WHERE id = :repo_name"""
        existing_portfolio = await database.fetch_one(
            portfolio_query, {"repo_name": repo_name}
        )
        
        if existing_portfolio:
            PORTFOLIO_ID = existing_portfolio["portfolio_id"]
            print(f"✅ Found portfolio: {PORTFOLIO_ID} for repo: {repo_name}")
        else:
            # Create new portfolio record
            new_uuid = str(uuid.uuid4())
            print(f"🔨 Creating new portfolio with UUID: {new_uuid}")
            
            insert_query = """
                INSERT INTO portfolios (portfolio_id, id, name, title, bio, 
                                      email, created_at)
                VALUES (:portfolio_id, :id, :name, :title, :bio, :email, NOW())
                RETURNING portfolio_id
            """
            result = await database.fetch_one(insert_query, {
                "portfolio_id": new_uuid,
                "id": repo_name,
                "name": f"Portfolio for {repo_name}",
                "title": "Software Engineer", 
                "bio": f"Auto-generated portfolio for {repo_name}",
                "email": "admin@example.com"
            })
            PORTFOLIO_ID = result["portfolio_id"] if result else new_uuid
            print(f"✅ Created portfolio: {PORTFOLIO_ID} for repo: {repo_name}")
        
        print(f"🔗 Connected to PostgreSQL: {get_database_url()}")
        print(f"🎯 Using portfolio ID: {PORTFOLIO_ID}")
        
        # Now that we have portfolio_id, log the initialization success
        try:
            from log_capture import add_log
            add_log("INFO", f"Portfolio initialized: {PORTFOLIO_ID} for {repo_name}",
                    "database", "init_database")
        except Exception as log_error:
            print(f"Could not log success: {log_error}")
        
    except Exception as e:
        print(f"❌ Error during portfolio initialization: {e}")
        import traceback
        error_traceback = traceback.format_exc()
        print(f"Full traceback: {error_traceback}")
        
        # Set a fallback portfolio ID to prevent crashes
        PORTFOLIO_ID = str(uuid.uuid4())
        print(f"⚠️  Using fallback portfolio ID: {PORTFOLIO_ID}")
        
        # Try to log the error (if possible)
        try:
            from log_capture import add_log
            add_log("ERROR", f"Portfolio init failed: {e}", "database", 
                   "init_database")
            # Log traceback separately
            add_log("ERROR", f"Portfolio init traceback: {error_traceback}", "database",
                   "init_database_traceback")
        except Exception as log_error:
            print(f"Could not log error: {log_error}")

def get_portfolio_id():
    """Get the current portfolio ID"""
    return PORTFOLIO_ID


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


# OAuth Token Functions
async def save_google_oauth_tokens(
    portfolio_id: str, access_token: str,
    refresh_token: str = None, expires_at: datetime = None,
    scopes: str = None, oauth_state: str = None
) -> Dict[str, Any]:
    """Save Google OAuth tokens to database with optional state"""
    query = """
    INSERT INTO google_oauth_tokens
    (portfolio_id, access_token, refresh_token,
     token_expires_at, granted_scopes, oauth_state, state_expires_at)
    VALUES (:portfolio_id, :access_token, :refresh_token,
            :token_expires_at, :granted_scopes, :oauth_state, :state_expires_at)
    ON CONFLICT (portfolio_id)
    DO UPDATE SET
        access_token = EXCLUDED.access_token,
        refresh_token = EXCLUDED.refresh_token,
        token_expires_at = EXCLUDED.token_expires_at,
        granted_scopes = EXCLUDED.granted_scopes,
        oauth_state = EXCLUDED.oauth_state,
        state_expires_at = EXCLUDED.state_expires_at,
        last_used_at = NOW(),
        updated_at = NOW()
    RETURNING id, portfolio_id, created_at
    """

    # Calculate state expiration (10 minutes from now)
    state_expires_at = None
    if oauth_state:
        from datetime import datetime, timezone, timedelta
        state_expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)

    values = {
        "portfolio_id": portfolio_id,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_expires_at": expires_at,
        "granted_scopes": scopes,
        "oauth_state": oauth_state,
        "state_expires_at": state_expires_at
    }

    result = await database.fetch_one(query, values)
    return {
        "id": result["id"],
        "portfolio_id": str(result["portfolio_id"]),
        "created_at": (result["created_at"].isoformat()
                       if result["created_at"] else None)
    }


async def get_google_oauth_tokens(
    portfolio_id: str
) -> Optional[Dict[str, Any]]:
    """Get Google OAuth tokens from database"""
    query = """
    SELECT id, portfolio_id, access_token, refresh_token,
           token_expires_at, granted_scopes, last_used_at, is_active,
           created_at, updated_at
    FROM google_oauth_tokens
    WHERE portfolio_id = :portfolio_id AND is_active = true
    ORDER BY updated_at DESC
    LIMIT 1
    """
    values = {"portfolio_id": portfolio_id}

    result = await database.fetch_one(query, values)
    if not result:
        return None

    return {
        "id": result["id"],
        "portfolio_id": str(result["portfolio_id"]),
        "access_token": result["access_token"],
        "refresh_token": result["refresh_token"],
        "token_expires_at": (result["token_expires_at"].isoformat()
                             if result["token_expires_at"] else None),
        "granted_scopes": result["granted_scopes"],
        "last_used_at": (result["last_used_at"].isoformat()
                         if result["last_used_at"] else None),
        "is_active": result["is_active"],
        "created_at": (result["created_at"].isoformat()
                       if result["created_at"] else None),
        "updated_at": (result["updated_at"].isoformat()
                       if result["updated_at"] else None)
    }


async def update_google_oauth_token_usage(
    portfolio_id: str
) -> bool:
    """Update last_used_at timestamp for OAuth token"""
    query = """
    UPDATE google_oauth_tokens
    SET last_used_at = NOW(), updated_at = NOW()
    WHERE portfolio_id = :portfolio_id AND is_active = true
    """

    result = await database.execute(
        query, {"portfolio_id": portfolio_id}
    )
    return result > 0


async def save_oauth_state_only(portfolio_id: str, state: str) -> bool:
    """Save only OAuth state for initiation, creating or updating the record as needed."""
    from datetime import datetime, timezone, timedelta
    
    state_expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    
    # Use INSERT ... ON CONFLICT to handle both new and existing users robustly.
    # This will create a new record if one doesn't exist for the portfolio_id,
    # or update the existing one if it does.
    query = """
    INSERT INTO google_oauth_tokens (portfolio_id, oauth_state, state_expires_at, updated_at)
    VALUES (:portfolio_id, :oauth_state, :state_expires_at, NOW())
    ON CONFLICT (portfolio_id)
    DO UPDATE SET
        oauth_state = EXCLUDED.oauth_state,
        state_expires_at = EXCLUDED.state_expires_at,
        updated_at = NOW()
    """
    
    params = {
        "portfolio_id": portfolio_id,
        "oauth_state": state,
        "state_expires_at": state_expires_at
    }
    
    await database.execute(query, params)
    
    # This operation should always succeed.
    return True


async def validate_oauth_state(portfolio_id: str, state: str) -> bool:
    """Validate OAuth state and clear it after use"""
    query = """
    SELECT id FROM google_oauth_tokens 
    WHERE portfolio_id = :portfolio_id
          AND oauth_state = :state
          AND state_expires_at > NOW()
    """
    
    result = await database.fetch_one(query, {
        "portfolio_id": portfolio_id,
        "state": state
    })
    
    if result:
        # Clear the state after successful validation
        clear_query = """
        UPDATE google_oauth_tokens 
        SET oauth_state = NULL, state_expires_at = NULL
        WHERE id = :id
        """
        await database.execute(clear_query, {"id": result["id"]})
        return True
    
    return False


async def validate_oauth_state_simple(state: str) -> bool:
    """Validate OAuth state without portfolio_id dependency"""
    query = """
    SELECT id FROM google_oauth_tokens 
    WHERE oauth_state = :state
          AND state_expires_at > NOW()
    """
    
    result = await database.fetch_one(query, {"state": state})
    
    if result:
        # Clear the state after successful validation
        clear_query = """
        UPDATE google_oauth_tokens 
        SET oauth_state = NULL, state_expires_at = NULL
        WHERE id = :id
        """
        await database.execute(clear_query, {"id": result["id"]})
        return True
    
    return False
