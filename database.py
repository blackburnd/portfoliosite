from databases import Database
from typing import List, Dict, Any, Optional
from datetime import datetime
import os
import uuid

# Centralized database configuration - SINGLE SOURCE OF TRUTH
def get_database_url() -> str:
    """Get database URL from environment variables."""
    database_url = os.getenv("_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError(
            "No _DATABASE_URL or DATABASE_URL environment variable set"
        )
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
        # Note: 'id' is the string field, 'portfolio_id' is the UUID
        # primary key
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
            add_log(
                "INFO",
                f"Portfolio initialized: {PORTFOLIO_ID} for {repo_name}",
                "database",
                "init_database"
            )
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
            add_log(
                "ERROR",
                f"Portfolio init failed: {e}",
                "database",
                "init_database"
            )
            # Log traceback separately
            add_log(
                "ERROR",
                f"Portfolio init traceback: {error_traceback}",
                "database",
                "init_database_traceback"
            )
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
    async def get_portfolio(
        portfolio_id: str = "daniel-blackburn"
    ) -> Optional[Dict[str, Any]]:
        """Get portfolio data with related work experience and projects"""

        # Get main portfolio data
        portfolio_query = """
        SELECT id, name, title, bio, tagline, profile_image,
               email, phone, vcard, resume_url, resume_download,
               github, twitter, skills, created_at, updated_at
        FROM portfolios
        WHERE id = :portfolio_id
        """

        portfolio = await database.fetch_one(
            portfolio_query, {"portfolio_id": portfolio_id}
        )
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
        work_exp = await database.fetch_all(
            work_query, {"portfolio_id": portfolio["id"]}
        )

        # Get projects
        projects_query = """
        SELECT id, title, description, url, image_url, technologies,
               sort_order
        FROM projects
        WHERE portfolio_id = :portfolio_id
        ORDER BY sort_order, created_at DESC
        """
        projects = await database.fetch_all(
            projects_query, {"portfolio_id": portfolio["id"]}
        )

        # Format the response
        created_at = portfolio["created_at"]
        updated_at = portfolio["updated_at"]
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
            "created_at": (
                created_at.isoformat() if isinstance(created_at, datetime)
                else created_at
            ),
            "updated_at": (
                updated_at.isoformat() if isinstance(updated_at, datetime)
                else updated_at
            ),
        }
    
    @staticmethod
    async def update_portfolio(
        portfolio_id: str, updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update portfolio information"""

        # Build dynamic update query
        set_clauses = []
        values = {"portfolio_id": portfolio_id}

        for key, value in updates.items():
            if key in [
                "name", "title", "bio", "tagline", "profile_image"
            ]:
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
    async def add_work_experience(
        portfolio_id: str, work_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Add new work experience"""

        query = """
        INSERT INTO work_experience
        (portfolio_id, company, position, location, start_date, end_date,
         description, is_current, company_url, sort_order)
        VALUES (:portfolio_id, :company, :position, :location, :start_date,
                :end_date, :description, :is_current, :company_url,
                :sort_order)
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

        new_work_exp = await database.fetch_one(query, values)
        return dict(new_work_exp) if new_work_exp else {}
    
    @staticmethod
    async def add_project(
        portfolio_id: str, project_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Add a new project"""

        query = """
        INSERT INTO projects
        (portfolio_id, title, description, url, image_url, technologies,
         sort_order)
        VALUES (:portfolio_id, :title, :description, :url, :image_url,
                :technologies, :sort_order)
        RETURNING id, title, description, url, image_url, technologies
        """

        values = {
            "portfolio_id": portfolio_id,
            "title": project_data["title"],
            "description": project_data.get("description"),
            "url": project_data.get("url"),
            "image_url": project_data.get("image_url"),
            "technologies": project_data.get("technologies"),
            "sort_order": project_data.get("sort_order", 0)
        }

        new_project = await database.fetch_one(query, values)
        return dict(new_project) if new_project else {}
    
    @staticmethod
    async def save_message(
        portfolio_id: str, message_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Save a new contact message to the database"""

        query = """
        INSERT INTO contact_messages
        (portfolio_id, name, email, message, source_ip, user_agent,
         status, notes)
        VALUES (:portfolio_id, :name, :email, :message, :source_ip,
                :user_agent, :status, :notes)
        RETURNING id, name, email, message, source_ip, user_agent, status,
                  notes, created_at
        """

        values = {
            "portfolio_id": portfolio_id,
            "name": message_data["name"],
            "email": message_data["email"],
            "message": message_data["message"],
            "source_ip": message_data.get("source_ip"),
            "user_agent": message_data.get("user_agent"),
            "status": "unread",
            "notes": ""
        }

        result = await database.fetch_one(query, values)
        created_at = result["created_at"]
        return {
            "id": result["id"],
            "name": result["name"],
            "email": result["email"],
            "message": result["message"],
            "source_ip": result["source_ip"],
            "user_agent": result["user_agent"],
            "status": result["status"],
            "notes": result["notes"],
            "created_at": (
                created_at.isoformat() if isinstance(created_at, datetime)
                else created_at
            ),
        }
    
    @staticmethod
    async def get_messages(
        portfolio_id: str = "daniel-blackburn"
    ) -> List[Dict[str, Any]]:
        """Get all contact messages for a portfolio"""

        query = """
        SELECT id, name, email, message, source_ip, user_agent, status,
               notes, created_at
        FROM contact_messages
        WHERE portfolio_id = :portfolio_id
        ORDER BY created_at DESC
        """

        results = await database.fetch_all(
            query, {"portfolio_id": portfolio_id}
        )

        messages = []
        for row in results:
            created_at = row["created_at"]
            messages.append({
                "id": row["id"],
                "name": row["name"],
                "email": row["email"],
                "message": row["message"],
                "source_ip": row["source_ip"],
                "user_agent": row["user_agent"],
                "status": row["status"],
                "notes": row["notes"],
                "created_at": (
                    created_at.isoformat()
                    if isinstance(created_at, datetime)
                    else created_at
                ),
            })
        return messages


db = PortfolioDatabase()


async def get_database():
    """Get database instance"""
    return db


async def create_oauth_session(
    portfolio_id: str, state: str, scopes: str, 
    auth_url: str, redirect_uri: str
) -> Dict[str, Any]:
    """
    Create an OAuth session record at the start of the workflow.
    This serves as the persistent datapoint for the entire OAuth handshake.
    """
    query = """
    INSERT INTO google_oauth_tokens
    (portfolio_id, oauth_state, requested_scopes, auth_url, redirect_uri, 
     workflow_status, is_active)
    VALUES (:portfolio_id, :oauth_state, :requested_scopes, :auth_url, 
            :redirect_uri, 'initiated', false)
    RETURNING id, portfolio_id, oauth_state, created_at
    """

    values = {
        "portfolio_id": portfolio_id,
        "oauth_state": state,
        "requested_scopes": scopes,
        "auth_url": auth_url,
        "redirect_uri": redirect_uri
    }

    result = await database.fetch_one(query, values)
    return {
        "id": result["id"],
        "portfolio_id": str(result["portfolio_id"]),
        "oauth_state": result["oauth_state"],
        "created_at": (result["created_at"].isoformat()
                       if result["created_at"] else None)
    }


async def update_oauth_session_with_callback(
    oauth_state: str, code: str, email: str = None, error: str = None
) -> bool:
    """
    Update the OAuth session with callback information.
    """
    if error:
        query = """
        UPDATE google_oauth_tokens
        SET workflow_status = 'failed', callback_error = :error, 
            callback_received_at = NOW()
        WHERE oauth_state = :oauth_state
        """
        values = {"oauth_state": oauth_state, "error": error}
    else:
        query = """
        UPDATE google_oauth_tokens
        SET workflow_status = 'callback_received', authorization_code = :code,
            admin_email = :email, callback_received_at = NOW()
        WHERE oauth_state = :oauth_state
        """
        values = {"oauth_state": oauth_state, "code": code, "email": email}
    
    await database.execute(query, values)
    return True


async def complete_oauth_session(
    oauth_state: str, access_token: str, refresh_token: str = None,
    expires_at: datetime = None, scopes: str = None
) -> bool:
    """
    Complete the OAuth session with final token information.
    """
    query = """
    UPDATE google_oauth_tokens
    SET workflow_status = 'completed', access_token = :access_token,
        refresh_token = :refresh_token, token_expires_at = :expires_at,
        granted_scopes = :scopes, is_active = true, completed_at = NOW()
    WHERE oauth_state = :oauth_state
    """
    
    values = {
        "oauth_state": oauth_state,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_at": expires_at,
        "scopes": scopes
    }
    
    await database.execute(query, values)
    return True


# OAuth Token Functions
async def save_google_oauth_tokens(
    portfolio_id: str, email: str, access_token: str,
    refresh_token: str = None, expires_at: datetime = None,
    scopes: str = None
) -> Dict[str, Any]:
    """
    Save Google OAuth tokens to database, creating a new record each time.
    """
    query = """
    INSERT INTO google_oauth_tokens
    (portfolio_id, admin_email, access_token, refresh_token,
     token_expires_at, granted_scopes, is_active)
    VALUES (:portfolio_id, :admin_email, :access_token, :refresh_token,
            :token_expires_at, :granted_scopes, :is_active)
    RETURNING id, portfolio_id, admin_email, created_at
    """

    values = {
        "portfolio_id": portfolio_id,
        "admin_email": email,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_expires_at": expires_at,
        "granted_scopes": scopes,
        "is_active": True
    }

    # Deactivate older tokens for the same user
    deactivate_query = """
    UPDATE google_oauth_tokens
    SET is_active = false
    WHERE portfolio_id = :portfolio_id
      AND admin_email = :admin_email
      AND is_active = true;
    """
    await database.execute(
        deactivate_query,
        {"portfolio_id": portfolio_id, "admin_email": email}
    )

    result = await database.fetch_one(query, values)
    return {
        "id": result["id"],
        "portfolio_id": str(result["portfolio_id"]),
        "admin_email": result["admin_email"],
        "created_at": (result["created_at"].isoformat()
                       if result["created_at"] else None)
    }


async def get_google_oauth_tokens(
    portfolio_id: str, email: str = None
) -> Optional[Dict[str, Any]]:
    """Get Google OAuth tokens from database"""
    if email:
        query = """
        SELECT id, portfolio_id, admin_email, access_token, refresh_token,
               token_expires_at, granted_scopes, last_used_at, is_active,
               created_at, updated_at
        FROM google_oauth_tokens
        WHERE portfolio_id = :portfolio_id AND admin_email = :email
              AND is_active = true
        ORDER BY updated_at DESC
        LIMIT 1
        """
        values = {"portfolio_id": portfolio_id, "email": email}
    else:
        query = """
        SELECT id, portfolio_id, admin_email, access_token, refresh_token,
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
        "admin_email": result["admin_email"],
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
    portfolio_id: str, email: str
) -> bool:
    """Update last_used_at timestamp for OAuth token"""
    query = """
    UPDATE google_oauth_tokens
    SET last_used_at = NOW(), updated_at = NOW()
    WHERE portfolio_id = :portfolio_id AND admin_email = :email
          AND is_active = true
    """

    result = await database.execute(
        query, {"portfolio_id": portfolio_id, "email": email}
    )
    return result > 0
