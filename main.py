# main.py - Lightweight FastAPI application with GraphQL and Google OAuth
import os
import secrets
import logging
import time
from datetime import datetime
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException, Depends, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, Response, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from strawberry.fastapi import GraphQLRouter
from pydantic import BaseModel
from typing import Optional, List

# Load environment variables from .env file
load_dotenv()
import uvicorn
import json
import os
import logging
from pathlib import Path
import sqlite3
import asyncio
import secrets
import hashlib
from log_capture import log_capture

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import our Google OAuth authentication module
from auth import (
    oauth, 
    get_current_user, 
    verify_token,
    is_authorized_user,
    create_user_session,
    create_access_token,
    get_auth_status
)
from cookie_auth import require_admin_auth_cookie
from linkedin_sync import linkedin_sync, LinkedInSyncError, LinkedInSync
from bootstrap_security import require_bootstrap_or_admin_auth, get_bootstrap_ui_context, mark_system_configured
from ttw_oauth_manager import TTWOAuthManager, TTWOAuthManagerError
from ttw_linkedin_sync import TTWLinkedInSync, TTWLinkedInSyncError

from app.resolvers import schema
try:
    from database import init_database, close_database, database
    DATABASE_AVAILABLE = True
except Exception as e:
    print(f"Database connection not available: {e}")
    DATABASE_AVAILABLE = False
    database = None

# Pydantic model for work item
class WorkItem(BaseModel):
    id: Optional[str]
    portfolio_id: str
    company: str
    position: str
    location: Optional[str]
    start_date: str
    end_date: Optional[str]
    description: Optional[str]
    is_current: Optional[bool] = False
    company_url: Optional[str]
    sort_order: Optional[int] = 0


# Pydantic model for project
class Project(BaseModel):
    id: Optional[str]
    portfolio_id: str
    title: str
    description: str
    url: Optional[str]
    image_url: Optional[str]
    technologies: Optional[List[str]] = []
    sort_order: Optional[int] = 0


# Pydantic models for bulk operations
class BulkWorkItemsRequest(BaseModel):
    items: List[WorkItem]


class BulkWorkItemsResponse(BaseModel):
    created: List[WorkItem]
    updated: List[WorkItem]
    errors: List[dict]


class BulkDeleteRequest(BaseModel):
    ids: List[str]


class BulkDeleteResponse(BaseModel):
    deleted_count: int
    errors: List[dict]


# Pydantic models for bulk project operations
class BulkProjectsRequest(BaseModel):
    items: List[Project]


class BulkProjectsResponse(BaseModel):
    created: List[Project]
    updated: List[Project]
    errors: List[dict]



# Initialize FastAPI app
app = FastAPI(
    title="Portfolio API",
    description="Lightweight GraphQL API for Daniel's Portfolio Website",
    version="1.0.0"
)

# Initialize TTW OAuth Manager  
ttw_oauth_manager = TTWOAuthManager()

# Add SessionMiddleware - required for OAuth authentication
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY", secrets.token_urlsafe(32)),
    max_age=3600,  # 1 hour
    https_only=os.getenv("ENV") == "production",
)

# Log startup configuration
logger.info("=== Application Startup ===")
logger.info(f"FastAPI app initialized: {app.title}")

# Security configuration
security = HTTPBasic()

# Admin credentials - In production, these should be in environment variables
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin")

logger.info(f"Admin username: {ADMIN_USERNAME}")
logger.info(f"Admin password: {'SET' if ADMIN_PASSWORD and ADMIN_PASSWORD != 'admin' else 'DEFAULT'}")
logger.info(f"Environment: {os.getenv('ENV', 'development')}")

# Log OAuth configuration from environment
oauth_configured = bool(os.getenv("GOOGLE_CLIENT_ID") and os.getenv("GOOGLE_CLIENT_SECRET"))
logger.info(f"OAuth configured: {oauth_configured}")
if oauth_configured:
    logger.info(f"OAuth redirect URI: {os.getenv('GOOGLE_REDIRECT_URI')}")
    logger.info(f"Authorized emails: {os.getenv('AUTHORIZED_EMAILS', 'none')}")
else:
    logger.warning("OAuth not configured - missing GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "your_secure_password_here")

def verify_admin_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    """Verify admin credentials for protected routes"""
    correct_username = secrets.compare_digest(credentials.username, ADMIN_USERNAME)
    correct_password = secrets.compare_digest(credentials.password, ADMIN_PASSWORD)
    
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

# CORS middleware
logger.info("=== Middleware Configuration ===")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
logger.info("CORS middleware configured")

# Add session middleware for OAuth
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY", "your-secret-key-change-this"),
    max_age=3600  # 1 hour
)
logger.info("Session middleware configured for OAuth")

# Add request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    method = request.method
    url = str(request.url)
    client_ip = request.client.host if request.client else "unknown"
    
    logger.info(f"=== Incoming Request ===")
    logger.info(f"Method: {method}")
    logger.info(f"URL: {url}")
    logger.info(f"Client IP: {client_ip}")
    logger.info(f"Headers: {dict(request.headers)}")
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        logger.info(f"Response status: {response.status_code}")
        logger.info(f"Process time: {process_time:.4f}s")
        return response
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(f"Request failed: {str(e)}", exc_info=True)
        logger.info(f"Process time: {process_time:.4f}s")
        raise

# GraphQL router
logger.info("=== GraphQL Configuration ===")
try:
    from app.resolvers import schema
    logger.info("GraphQL schema imported successfully")
    graphql_app = GraphQLRouter(schema)
    app.include_router(graphql_app, prefix="/graphql")
    logger.info("GraphQL router initialized and mounted at /graphql")
except ImportError as e:
    logger.error(f"Failed to import GraphQL schema: {str(e)}", exc_info=True)
    raise
except Exception as e:
    logger.error(f"GraphQL initialization error: {str(e)}", exc_info=True)
    raise

# Create directories if they don't exist
os.makedirs("app/assets/img", exist_ok=True)
os.makedirs("app/assets/files", exist_ok=True)
os.makedirs("templates", exist_ok=True)

# Custom StaticFiles class that enables directory browsing
class BrowsableStaticFiles(StaticFiles):
    def __init__(self, *, directory: str):
        super().__init__(directory=directory, html=True)
        self.directory = Path(directory)

    async def get_response(self, path: str, scope):
        try:
            return await super().get_response(path, scope)
        except Exception:
            # If file not found, try to serve directory listing
            full_path = self.directory / path.lstrip('/')
            if full_path.is_dir():
                return self.directory_listing(full_path, path)
            raise

    def directory_listing(self, directory: Path, url_path: str):
        """Generate HTML directory listing"""
        items = []
        if url_path != '/':
            items.append('<li><a href="../">../</a></li>')
        
        for item in sorted(directory.iterdir()):
            if item.is_dir():
                items.append(f'<li><a href="{item.name}/">{item.name}/</a></li>')
            else:
                size = item.stat().st_size
                size_str = f" ({size:,} bytes)"
                items.append(f'<li><a href="{item.name}">{item.name}</a>{size_str}</li>')
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Directory listing for {url_path}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                h1 {{ color: #333; }}
                ul {{ list-style: none; padding: 0; }}
                li {{ margin: 8px 0; }}
                a {{ text-decoration: none; color: #0066cc; }}
                a:hover {{ text-decoration: underline; }}
            </style>
        </head>
        <body>
            <h1>Directory listing for {url_path}</h1>
            <ul>
                {"".join(items)}
            </ul>
        </body>
        </html>
        """
        return Response(content=html, media_type="text/html")

# Mount static files with directory browsing enabled
app.mount("/assets", BrowsableStaticFiles(directory="assets"), name="assets")
templates = Jinja2Templates(directory="templates")


# Add favicon route to prevent 404 errors
@app.get("/favicon.ico")
async def favicon():
    """Return a 204 No Content for favicon requests to avoid 404 errors"""
    return Response(status_code=204)


# Database initialization
@app.on_event("startup")
async def startup_event():
    logger.info("=== Database Startup ===")
    try:
        if DATABASE_AVAILABLE:
            logger.info("Initializing database connection...")
            await init_database()
            logger.info("Database initialized successfully")
        else:
            logger.warning("Running without database connection")
    except Exception as e:
        logger.error(f"Startup error: {str(e)}", exc_info=True)
        raise


@app.on_event("shutdown")
async def shutdown_event():
    if DATABASE_AVAILABLE:
        await close_database()


# --- Google OAuth Authentication Routes ---

@app.get("/auth/login")
async def auth_login(request: Request):
    """Initiate Google OAuth login"""
    try:
        logger.info("=== OAuth Login Request Started ===")
        
        # Check if OAuth is properly configured
        if not oauth or not oauth.google:
            logger.error("OAuth not configured - missing credentials")
            return HTMLResponse(
                content="""
                <html><body>
                <h1>Authentication Not Available</h1>
                <p>Google OAuth is not configured on this server.</p>
                <p>Missing GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET environment variables.</p>
                <p><a href="/">Return to main site</a></p>
                </body></html>
                """, 
                status_code=503
            )
        
        # Check environment variables at runtime
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET") 
        redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/callback")
        
        if not client_id or not client_secret:
            logger.error("Missing OAuth environment variables")
            return HTMLResponse(
                content="""
                <html><body>
                <h1>OAuth Configuration Error</h1>
                <p>Missing required environment variables for Google OAuth.</p>
                <p><a href="/">Return to main site</a></p>
                </body></html>
                """, 
                status_code=503
            )
        
        logger.info(f"Using redirect URI: {redirect_uri}")
        
        # Clear any existing session state to prevent CSRF issues
        request.session.clear()
        
        # Generate a new state parameter for CSRF protection
        import secrets
        state = secrets.token_urlsafe(32)
        request.session['oauth_state'] = state
        
        logger.info("Initiating OAuth redirect with fresh state...")
        
        # Use the OAuth client to redirect with proper state handling
        google = oauth.google
        try:
            result = await google.authorize_redirect(
                request, 
                redirect_uri,
                state=state
            )
            logger.info("OAuth redirect created successfully")
        except Exception as redirect_error:
            logger.error(f"OAuth redirect error: {str(redirect_error)}")
            raise
        
        logger.info("OAuth redirect created successfully")
        return result
        
    except Exception as e:
        logger.error(f"OAuth login error: {str(e)}")
        logger.exception("Full traceback:")
        return HTMLResponse(
            content=f"""
            <html><body>
            <h1>OAuth Login Failed</h1>
            <p>Error: {str(e)}</p>
            <p><a href="/">Return to main site</a></p>
            </body></html>
            """, 
            status_code=500
        )


@app.get("/auth/callback")
async def auth_callback(request: Request):
    """Handle Google OAuth callback"""
    logger.info("=== OAuth Callback Received ===")
    logger.info(f"Callback URL: {request.url}")
    logger.info(f"Query params: {dict(request.query_params)}")
    
    try:
        # Check if OAuth is properly configured
        if not oauth or not oauth.google:
            logger.error("OAuth not configured in callback")
            return HTMLResponse(
                content="""
                <html><body>
                <h1>Authentication Error</h1>
                <p>Google OAuth is not configured on this server.</p>
                <p><a href="/">Return to main site</a></p>
                </body></html>
                """, 
                status_code=503
            )
        
        # Validate state parameter to prevent CSRF attacks
        received_state = request.query_params.get('state')
        session_state = request.session.get('oauth_state')
        
        if not received_state or not session_state:
            logger.error("Missing state parameters in OAuth callback")
            return HTMLResponse(
                content="""
                <html><body>
                <h1>Authentication Error</h1>
                <p>Invalid OAuth state. Please try logging in again.</p>
                <p><a href="/auth/login">Try again</a> | <a href="/">Return to main site</a></p>
                </body></html>
                """, 
                status_code=400
            )
        
        if received_state != session_state:
            logger.error(f"State mismatch: received={received_state}, session={session_state}")
            return HTMLResponse(
                content="""
                <html><body>
                <h1>Authentication Error</h1>
                <p>OAuth state mismatch detected (CSRF protection). Please try logging in again.</p>
                <p><a href="/auth/login">Try again</a> | <a href="/">Return to main site</a></p>
                </body></html>
                """, 
                status_code=400
            )
        
        logger.info("State validation passed, exchanging code for token...")
        google = oauth.google
        token = await google.authorize_access_token(request)
        logger.info(f"Token received: {bool(token)}")
        
        # Clear the OAuth state from session
        request.session.pop('oauth_state', None)
        
        user_info = token.get('userinfo')
        
        if not user_info:
            # Fallback to get user info from Google
            resp = await google.get('https://www.googleapis.com/oauth2/v1/userinfo', token=token)
            user_info = resp.json()
        
        email = user_info.get('email')
        if not email:
            return HTMLResponse(
                content="""
                <html><body>
                <h1>Authentication Error</h1>
                <p>No email found in Google account.</p>
                <p><a href="/auth/login">Try again</a> | <a href="/">Return to main site</a></p>
                </body></html>
                """, 
                status_code=400
            )
        
        if not is_authorized_user(email):
            return HTMLResponse(
                content=f"""
                <html><body>
                <h1>Access Denied</h1>
                <p>Your email ({email}) is not authorized to access this admin panel.</p>
                <p><a href="/">Return to main site</a></p>
                </body></html>
                """, 
                status_code=403
            )
        
        # Create JWT token
        session_data = create_user_session(user_info)
        access_token = create_access_token(session_data)
        
        # Redirect to admin page with token
        response = RedirectResponse(url="/workadmin")
        
        # Set secure cookie based on environment
        is_production = os.getenv("ENV") == "production"
        
        response.set_cookie(
            key="access_token",
            value=f"Bearer {access_token}",
            httponly=True,
            secure=is_production,  # True in production with HTTPS
            samesite="lax",
            max_age=28800  # 8 hours
        )
        
        logger.info(f"Authentication successful for {email}")
        return response
        
    except Exception as e:
        logger.error(f"OAuth callback error: {str(e)}")
        logger.exception("Full traceback:")
        return HTMLResponse(
            content=f"""
            <html><body>
            <h1>Authentication Failed</h1>
            <p>Error: {str(e)}</p>
            <p><a href="/auth/login">Try again</a> | <a href="/">Return to main site</a></p>
            </body></html>
            """, 
            status_code=400
        )


@app.get("/auth/logout")
async def logout(response: Response):
    """Log out the user by clearing the authentication cookie"""
    try:
        logger.info("=== OAuth Logout Request ===")
        response.delete_cookie(key="access_token", path="/")
        logger.info("Successfully cleared authentication cookie")
        return RedirectResponse(url="/", status_code=303)
    except Exception as e:
        logger.error(f"Logout error: {str(e)}", exc_info=True)
        return RedirectResponse(url="/", status_code=303)


@app.get("/auth/status")
async def auth_status():
    """Get authentication configuration status"""
    return get_auth_status()


# Routes for serving the portfolio website
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Serve the main portfolio page"""
    # Check if user is authenticated
    user_authenticated = False
    user_email = None
    
    try:
        # Try to get token from cookies
        token = request.cookies.get("access_token")
        if token:
            payload = verify_token(token)
            email = payload.get("sub")
            if email and is_authorized_user(email):
                user_authenticated = True
                user_email = email
    except Exception:
        # Ignore authentication errors for public page
        pass
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "title": "Daniel Blackburn - Building innovative solutions",
        "current_page": "home",
        "user_authenticated": user_authenticated,
        "user_email": user_email,
        "user_info": {"email": user_email} if user_authenticated else None
    })

@app.get("/contact/", response_class=HTMLResponse)
async def contact(request: Request):
    """Serve the contact page"""
    # Check if user is authenticated
    user_authenticated = False
    user_email = None
    
    try:
        # Try to get token from cookies
        token = request.cookies.get("access_token")
        if token:
            payload = verify_token(token)
            email = payload.get("sub")
            if email and is_authorized_user(email):
                user_authenticated = True
                user_email = email
    except Exception:
        # Ignore authentication errors for public page
        pass
    
    return templates.TemplateResponse("contact.html", {
        "request": request,
        "title": "Contact - Daniel Blackburn",
        "current_page": "contact",
        "user_authenticated": user_authenticated,
        "user_email": user_email,
        "user_info": {"email": user_email} if user_authenticated else None
    })

@app.post("/contact/submit")
async def contact_submit(request: Request):
    """Handle contact form submission"""
    form_data = await request.form()
    
    # In a real implementation, this would save to database or send email
    # For now, just return a simple response
    return {
        "status": "success",
        "message": "Thank you for your message! I'll get back to you soon.",
        "data": {
            "name": form_data.get("name"),
            "email": form_data.get("email"),
            "subject": form_data.get("subject"),
            "message": form_data.get("message")
        }
    }

@app.get("/work/", response_class=HTMLResponse)
async def work(request: Request):
    """Serve the work page"""
    # Check if user is authenticated
    user_authenticated = False
    user_email = None
    
    try:
        # Try to get token from cookies
        token = request.cookies.get("access_token")
        if token:
            payload = verify_token(token)
            email = payload.get("sub")
            if email and is_authorized_user(email):
                user_authenticated = True
                user_email = email
    except Exception:
        # Ignore authentication errors for public page
        pass
    
    return templates.TemplateResponse("work.html", {
        "request": request,
        "title": "Featured projects, and work - daniel blackburn",
        "current_page": "work",
        "user_authenticated": user_authenticated,
        "user_email": user_email
    })

@app.get("/work/{project_slug}/", response_class=HTMLResponse)
async def project_detail(request: Request, project_slug: str):
    """Serve individual project pages"""
    return templates.TemplateResponse("project.html", {
        "request": request,
        "project_slug": project_slug,
        "title": f"Project - daniel blackburn"
    })

@app.get("/resume/")
async def resume():
    """Redirect to local resume PDF file"""
    return RedirectResponse(
        url="/assets/files/danielblackburn.pdf",  # Updated to match your actual filename
        status_code=302
    )

# Direct download route for resume
from fastapi.responses import FileResponse

@app.get("/resume/download/")
async def resume_download():
    """Serve resume PDF as attachment for download."""
    return FileResponse(
        path="assets/files/danielblackburn.pdf",
        media_type="application/pdf",
        filename="danielblackburn.pdf",
        headers={"Content-Disposition": "attachment; filename=danielblackburn.pdf"}
    )


@app.get("/projects/", response_class=HTMLResponse)
async def projects(request: Request):
    """Serve the projects page"""
    return templates.TemplateResponse("projects.html", {
        "request": request,
        "title": "Projects - Daniel Blackburn",
        "current_page": "projects"
    })


# --- Work Admin Page ---
@app.get("/workadmin", response_class=HTMLResponse)
async def work_admin_page(
    request: Request,
    admin: dict = Depends(require_admin_auth_cookie)
):
    return templates.TemplateResponse("workadmin.html", {
        "request": request,
        "current_page": "workadmin",
        "user_info": admin,
        "user_authenticated": True,
        "user_email": admin.get("email", "")
    })


@app.get("/workadmin/bulk", response_class=HTMLResponse)
async def work_admin_bulk_page(
    request: Request,
    admin: dict = Depends(require_admin_auth_cookie)
):
    """New bulk editor interface for work items"""
    return templates.TemplateResponse("workadmin_bulk.html", {
        "request": request,
        "current_page": "workadmin_bulk",
        "user_info": admin,
        "user_authenticated": True,
        "user_email": admin.get("email", "")
    })


# --- Logs Admin Page ---
@app.get("/debug/test")
async def debug_test():
    """Simple test route to verify deployment"""
    return {"status": "ok", "message": "Debug route working", "timestamp": time.time()}


@app.get("/debug/logs", response_class=HTMLResponse)
async def logs_admin_page(request: Request):
    """Admin page for viewing application logs (no auth required for debugging)"""
    return templates.TemplateResponse("logs.html", {
        "request": request,
        "current_page": "logs",
        "user_info": {"email": "debug@example.com", "name": "Debug User"},
        "user_authenticated": True,
        "user_email": "debug@example.com"
    })


@app.get("/debug/logs/data")
async def get_logs_data():
    """API endpoint to get log data as JSON (no auth required for debugging)"""
    logs = log_capture.get_logs()
    stats = log_capture.get_stats()
    return JSONResponse({
        "logs": logs,
        "stats": stats
    })


@app.post("/debug/logs/clear")
async def clear_logs_data():
    """API endpoint to clear all logs (no auth required for debugging)"""
    log_capture.clear_logs()
    return JSONResponse({"status": "success", "message": "Logs cleared"})


# --- Redirect admin/logs to debug/logs for convenience ---
@app.get("/admin/logs")
async def admin_logs_redirect():
    """Redirect admin logs to debug logs for debugging without auth"""
    return RedirectResponse(url="/debug/logs", status_code=302)


# --- Projects Admin Page ---
@app.get("/projectsadmin", response_class=HTMLResponse)
async def projects_admin_page(
    request: Request,
    admin: dict = Depends(require_admin_auth_cookie)
):
    return templates.TemplateResponse("projectsadmin.html", {
        "request": request,
        "current_page": "projectsadmin",
        "user_info": admin,
        "user_authenticated": True,
        "user_email": admin.get("email", "")
    })


@app.get("/projectsadmin/bulk", response_class=HTMLResponse)
async def projects_admin_bulk_page(
    request: Request,
    admin: dict = Depends(require_admin_auth_cookie)
):
    """New bulk editor interface for projects"""
    return templates.TemplateResponse("projectsadmin_bulk.html", {
        "request": request,
        "current_page": "projectsadmin_bulk",
        "user_info": admin,
        "user_authenticated": True,
        "user_email": admin.get("email", "")
    })


@app.get("/linkedin", response_class=HTMLResponse)
async def linkedin_admin_page(request: Request, user: dict = Depends(require_bootstrap_or_admin_auth)):
    """LinkedIn sync admin interface - redirects to bootstrap if not configured"""
    try:
        # Check if LinkedIn OAuth is configured
        admin_email = user.get('email') if user else 'bootstrap_user@system.local'
        sync_service = TTWLinkedInSync(admin_email)
        app_status = await sync_service.get_oauth_app_status()
        
        # If OAuth app is not configured, redirect to bootstrap setup
        if not app_status.get('configured', False):
            logger.info("LinkedIn OAuth not configured - redirecting to bootstrap setup")
            return RedirectResponse(url="/oauth/bootstrap", status_code=302)
        
        # OAuth is configured, show admin interface
        return templates.TemplateResponse("linkedin_admin.html", {
            "request": request,
            "current_page": "linkedin_admin",
            "user_info": user,
            "user_authenticated": bool(user),
            "user_email": user.get("email", "") if user else ""
        })
        
    except Exception as e:
        logger.error(f"Error loading LinkedIn admin page: {str(e)}")
        # On error, redirect to bootstrap setup as fallback
        return RedirectResponse(url="/oauth/bootstrap", status_code=302)


# --- LinkedIn Sync Admin Endpoints ---

@app.get("/linkedin/status")
async def linkedin_sync_status(admin: dict = Depends(require_admin_auth_cookie)):
    """Get LinkedIn sync configuration and connection status"""
    try:
        admin_email = admin.get('email')
        sync_service = TTWLinkedInSync(admin_email)
        status = await sync_service.get_connection_status()
        
        return JSONResponse({
            "status": "success",
            "linkedin_sync": status
        })
    except Exception as e:
        logger.error(f"Error getting LinkedIn sync status: {str(e)}")
        return JSONResponse({
            "status": "error",
            "error": str(e)
        }, status_code=500)


# --- Database Schema Setup Endpoint ---

@app.get("/admin/oauth-status")
async def get_oauth_status():
    """Show current OAuth configuration status - no auth required"""
    try:
        # Check linkedin_oauth_config table
        linkedin_query = """
            SELECT id, app_name, client_id, redirect_uri, is_active, configured_by_email, created_at
            FROM linkedin_oauth_config 
            ORDER BY created_at DESC
        """
        linkedin_configs = await database.fetch_all(linkedin_query)
        
        # Check oauth_apps table  
        oauth_apps_query = """
            SELECT id, provider, app_name, client_id, redirect_uri, is_active, created_by, created_at
            FROM oauth_apps 
            ORDER BY created_at DESC
        """
        try:
            oauth_apps = await database.fetch_all(oauth_apps_query)
        except:
            oauth_apps = []
        
        # Check oauth_system_settings table
        system_settings_query = """
            SELECT setting_key, setting_value, description, created_by, created_at
            FROM oauth_system_settings 
            ORDER BY created_at DESC
        """
        try:
            system_settings = await database.fetch_all(system_settings_query)
        except:
            system_settings = []
        
        return JSONResponse({
            "status": "success",
            "linkedin_oauth_configs": [dict(row) for row in linkedin_configs],
            "oauth_apps": [dict(row) for row in oauth_apps],
            "system_settings": [dict(row) for row in system_settings],
            "total_linkedin_configs": len(linkedin_configs),
            "total_oauth_apps": len(oauth_apps),
            "total_system_settings": len(system_settings)
        })
        
    except Exception as e:
        logger.error(f"Error getting OAuth status: {str(e)}")
        return JSONResponse({
            "status": "error",
            "error": str(e)
        }, status_code=500)

@app.get("/admin/setup-oauth-tables")
async def setup_oauth_tables():
    """Create missing OAuth tables - admin endpoint"""
    try:
        # Create oauth_system_settings table
        oauth_system_settings_sql = """
        CREATE TABLE IF NOT EXISTS oauth_system_settings (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            setting_key VARCHAR(100) UNIQUE NOT NULL,
            setting_value TEXT NOT NULL,
            description TEXT,
            is_encrypted BOOLEAN DEFAULT false,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            created_by VARCHAR(255) NOT NULL
        );
        """
        
        # Create oauth_apps table  
        oauth_apps_sql = """
        CREATE TABLE IF NOT EXISTS oauth_apps (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            provider VARCHAR(50) NOT NULL,
            app_name VARCHAR(255) NOT NULL,
            client_id VARCHAR(255) NOT NULL,
            client_secret TEXT NOT NULL,
            redirect_uri VARCHAR(500) NOT NULL,
            scopes TEXT[],
            is_active BOOLEAN DEFAULT true,
            encryption_key TEXT NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            created_by VARCHAR(255) NOT NULL,
            UNIQUE(provider, app_name)
        );
        """
        
        # Execute table creation
        await database.execute(oauth_system_settings_sql)
        await database.execute(oauth_apps_sql)
        
        return JSONResponse({
            "status": "success",
            "message": "OAuth tables created successfully",
            "tables_created": ["oauth_system_settings", "oauth_apps"]
        })
        
    except Exception as e:
        logger.error(f"Error creating OAuth tables: {str(e)}")
        return JSONResponse({
            "status": "error", 
            "error": str(e)
        }, status_code=500)

# --- LinkedIn OAuth App Configuration Endpoints ---

@app.get("/oauth/bootstrap")
async def oauth_bootstrap_page(request: Request):
    """Bootstrap OAuth configuration page - accessible without authentication"""
    try:
        # Get bootstrap context
        bootstrap_context = await get_bootstrap_ui_context(request)
        
        return templates.TemplateResponse("oauth_bootstrap.html", {
            "request": request,
            "bootstrap": bootstrap_context["bootstrap"],
            "user": bootstrap_context["user"],
            "auth_status": bootstrap_context["auth_status"]
        })
    except Exception as e:
        logger.error(f"Error loading OAuth bootstrap page: {str(e)}")
        return HTMLResponse(f"<h1>Error</h1><p>Failed to load OAuth configuration page: {e}</p>", status_code=500)

@app.get("/linkedin/oauth/config")
async def get_linkedin_oauth_config(request: Request):
    """Get LinkedIn OAuth app configuration status - TTW management interface"""
    try:
        # Get LinkedIn OAuth configuration directly from database
        query = """
            SELECT app_name, client_id, redirect_uri, is_active, configured_by_email, created_at
            FROM linkedin_oauth_config 
            WHERE is_active = true
            ORDER BY created_at DESC
            LIMIT 1
        """
        result = await database.fetch_one(query)
        
        if result:
            oauth_app = {
                "configured": True,
                "app_name": result["app_name"],
                "client_id": result["client_id"],
                "redirect_uri": result["redirect_uri"],
                "is_active": result["is_active"],
                "configured_by_email": result["configured_by_email"],
                "created_at": result["created_at"].isoformat() if result["created_at"] else None
            }
        else:
            oauth_app = {"configured": False}
        
        return JSONResponse({
            "status": "success",
            "oauth_app": oauth_app,
            "available_scopes": [
                {"name": "r_liteprofile", "description": "Access to basic profile information"},
                {"name": "r_emailaddress", "description": "Access to email address"}
            ]
        })
    except Exception as e:
        logger.error(f"Error getting LinkedIn OAuth config: {str(e)}")
        return JSONResponse({
            "status": "error",
            "error": str(e)
        }, status_code=500)

@app.post("/linkedin/oauth/config")
async def configure_linkedin_oauth_app(request: Request):
    """Configure LinkedIn OAuth app - TTW management interface (no authentication required)"""
    try:
        # Use default admin email for TTW configuration
        admin_email = 'ttw_user@system.local'
        config_data = await request.json()
        
        # Validate required fields
        required_fields = ["client_id", "client_secret", "redirect_uri"]
        for field in required_fields:
            if not config_data.get(field):
                return JSONResponse({
                    "status": "error",
                    "error": f"Missing required field: {field}"
                }, status_code=400)
        
        # Configure OAuth app
        success = await ttw_oauth_manager.configure_oauth_app(admin_email, config_data)
        
        if success:
            return JSONResponse({
                "status": "success",
                "message": "LinkedIn OAuth app configured successfully",
                "ttw_mode": True
            })
        else:
            return JSONResponse({
                "status": "error",
                "error": "Failed to configure LinkedIn OAuth app"
            }, status_code=500)
            
    except Exception as e:
        logger.error(f"Error configuring LinkedIn OAuth app: {str(e)}")
        return JSONResponse({
            "status": "error",
            "error": str(e)
        }, status_code=500)


# --- LinkedIn OAuth User Connection Endpoints ---

@app.get("/linkedin/oauth/authorize")
async def linkedin_oauth_authorize(
    admin: dict = Depends(require_admin_auth_cookie),
    scopes: str = None
):
    """Initiate LinkedIn OAuth flow with selected scopes"""
    try:
        admin_email = admin.get('email')
        
        # Parse requested scopes
        requested_scopes = None
        if scopes:
            requested_scopes = scopes.split(',')
        
        auth_url, state = await ttw_oauth_manager.get_linkedin_authorization_url(admin_email, requested_scopes)
        
        return JSONResponse({
            "status": "success",
            "authorization_url": auth_url,
            "state": state
        })
    except TTWOAuthManagerError as e:
        logger.error(f"LinkedIn OAuth authorization error: {str(e)}")
        return JSONResponse({
            "status": "error",
            "error": str(e)
        }, status_code=400)
    except Exception as e:
        logger.error(f"Unexpected LinkedIn OAuth error: {str(e)}")
        return JSONResponse({
            "status": "error",
            "error": "Internal server error"
        }, status_code=500)

@app.get("/admin/linkedin/callback")
async def linkedin_oauth_callback(
    request: Request,
    code: str = None,
    state: str = None,
    error: str = None
):
    """Handle LinkedIn OAuth callback"""
    try:
        if error:
            logger.error(f"LinkedIn OAuth error: {error}")
            return templates.TemplateResponse("linkedin_oauth_error.html", {
                "request": request,
                "error": error
            })
        
        if not code or not state:
            raise ValueError("Missing authorization code or state")
        
        # Verify state and extract admin email and requested scopes
        state_data = ttw_oauth_manager.verify_linkedin_state(state)
        admin_email = state_data["admin_email"]
        
        # Exchange code for tokens and store connection
        token_data = await ttw_oauth_manager.exchange_linkedin_code_for_tokens(code, state_data)
        
        logger.info(f"LinkedIn OAuth successful for admin: {admin_email}")
        return templates.TemplateResponse("linkedin_oauth_success.html", {
            "request": request,
            "admin_email": admin_email,
            "granted_scopes": token_data["granted_scopes"],
            "profile_name": token_data["profile"].get("localizedFirstName", "User"),
            "success": True
        })
        
    except TTWOAuthManagerError as e:
        logger.error(f"LinkedIn OAuth callback error: {str(e)}")
        return templates.TemplateResponse("linkedin_oauth_error.html", {
            "request": request,
            "error": str(e)
        })
    except Exception as e:
        logger.error(f"Unexpected LinkedIn OAuth callback error: {str(e)}")
        return templates.TemplateResponse("linkedin_oauth_error.html", {
            "request": request,
            "error": "Internal server error during authentication"
        })

@app.delete("/linkedin/oauth/disconnect")
async def linkedin_oauth_disconnect(admin: dict = Depends(require_admin_auth_cookie)):
    """Disconnect LinkedIn OAuth"""
    try:
        admin_email = admin.get('email')
        sync_service = TTWLinkedInSync(admin_email)
        success = await sync_service.disconnect_linkedin()
        
        if success:
            return JSONResponse({
                "status": "success",
                "message": "LinkedIn account disconnected successfully"
            })
        else:
            return JSONResponse({
                "status": "error",
                "error": "Failed to disconnect LinkedIn account"
            }, status_code=500)
            
    except Exception as e:
        logger.error(f"LinkedIn OAuth disconnect error: {str(e)}")
        return JSONResponse({
            "status": "error",
            "error": str(e)
        }, status_code=500)


# --- LinkedIn Data Sync Endpoints ---

@app.post("/linkedin/sync/profile")
async def sync_linkedin_profile(admin: dict = Depends(require_admin_auth_cookie)):
    """Sync LinkedIn profile data to portfolio"""
    try:
        admin_email = admin.get('email', 'unknown')
        logger.info(f"LinkedIn profile sync initiated by user: {admin_email}")
        
        sync_service = TTWLinkedInSync(admin_email)
        result = await sync_service.sync_profile_data({
            "basic_info": True,
            "work_experience": False,
            "skills": False
        })
        
        return JSONResponse({
            "status": "success",
            "result": result
        })
    except TTWLinkedInSyncError as e:
        logger.error(f"LinkedIn profile sync error: {str(e)}")
        return JSONResponse({
            "status": "error",
            "error": str(e)
        }, status_code=400)
    except Exception as e:
        logger.error(f"Unexpected error during LinkedIn profile sync: {str(e)}")
        return JSONResponse({
            "status": "error", 
            "error": "Internal server error during sync"
        }, status_code=500)


@app.post("/linkedin/sync/experience")
async def sync_linkedin_experience(admin: dict = Depends(require_admin_auth_cookie)):
    """Sync LinkedIn work experience data to database"""
    try:
        admin_email = admin.get('email', 'unknown')
        logger.info(f"LinkedIn experience sync initiated by user: {admin_email}")
        
        sync_service = TTWLinkedInSync(admin_email)
        result = await sync_service.sync_profile_data({
            "basic_info": False,
            "work_experience": True,
            "skills": False
        })
        
        return JSONResponse({
            "status": "success",
            "result": result
        })
    except TTWLinkedInSyncError as e:
        logger.error(f"LinkedIn experience sync error: {str(e)}")
        return JSONResponse({
            "status": "error",
            "error": str(e)
        }, status_code=400)
    except Exception as e:
        logger.error(f"Unexpected error during LinkedIn experience sync: {str(e)}")
        return JSONResponse({
            "status": "error",
            "error": "Internal server error during sync"
        }, status_code=500)


@app.post("/linkedin/sync/full")
async def sync_linkedin_full(admin: dict = Depends(require_admin_auth_cookie)):
    """Perform full LinkedIn sync (profile + experience + skills)"""
    try:
        admin_email = admin.get('email', 'unknown')
        logger.info(f"Full LinkedIn sync initiated by user: {admin_email}")
        
        sync_service = TTWLinkedInSync(admin_email)
        result = await sync_service.sync_profile_data({
            "basic_info": True,
            "work_experience": True,
            "skills": True
        })
        
        return JSONResponse({
            "status": "success",
            "result": result
        })
    except TTWLinkedInSyncError as e:
        logger.error(f"LinkedIn full sync error: {str(e)}")
        return JSONResponse({
            "status": "error",
            "error": str(e)
        }, status_code=400)
    except Exception as e:
        logger.error(f"Unexpected error during LinkedIn full sync: {str(e)}")
        return JSONResponse({
            "status": "error",
            "error": "Internal server error during sync"
        }, status_code=500)

@app.get("/linkedin/sync/history")
async def get_linkedin_sync_history(admin: dict = Depends(require_admin_auth_cookie)):
    """Get LinkedIn sync history"""
    try:
        admin_email = admin.get('email')
        sync_service = TTWLinkedInSync(admin_email)
        history = await sync_service.get_sync_history()
        
        return JSONResponse({
            "status": "success",
            "history": history
        })
    except Exception as e:
        logger.error(f"Error getting LinkedIn sync history: {str(e)}")
        return JSONResponse({
            "status": "error",
            "error": str(e)
        }, status_code=500)


# --- CRUD Endpoints for Work Items ---

# List all work items
@app.get("/workitems", response_model=List[WorkItem])
async def list_workitems():
    if not DATABASE_AVAILABLE:
        # Return sample data for testing
        return [
            WorkItem(
                id="sample-1",
                portfolio_id="daniel-blackburn",
                company="Sample Company",
                position="Software Engineer",
                location="Remote",
                start_date="2023",
                end_date="",
                description="Sample work experience for testing",
                is_current=True,
                company_url="https://example.com",
                sort_order=1
            )
        ]
    
    try:
        # Check if table exists - different for SQLite vs PostgreSQL
        database_url = os.getenv("DATABASE_URL", "")
        if "sqlite" in database_url.lower():
            # SQLite syntax
            check_table = ("SELECT name FROM sqlite_master "
                          "WHERE type='table' AND name='work_experience'")
            table_exists = await database.fetch_val(check_table)
        else:
            # PostgreSQL syntax
            check_table = "SELECT to_regclass('work_experience')"
            table_exists = await database.fetch_val(check_table)
        
        if not table_exists:
            # Return empty list if table doesn't exist
            return []
            
        query = "SELECT * FROM work_experience ORDER BY sort_order, start_date DESC"
        rows = await database.fetch_all(query)
        
        # Convert rows to WorkItem objects, handling any missing fields
        work_items = []
        for row in rows:
            row_dict = dict(row)
            # Ensure all required fields have default values
            work_item_data = {
                "id": str(row_dict.get("id", "")),
                "portfolio_id": row_dict.get("portfolio_id", "daniel-blackburn"),
                "company": row_dict.get("company", ""),
                "position": row_dict.get("position", ""),
                "location": row_dict.get("location"),
                "start_date": row_dict.get("start_date", ""),
                "end_date": row_dict.get("end_date"),
                "description": row_dict.get("description"),
                "is_current": row_dict.get("is_current", False),
                "company_url": row_dict.get("company_url"),
                "sort_order": row_dict.get("sort_order", 0)
            }
            work_items.append(WorkItem(**work_item_data))
        
        return work_items
        
    except Exception as e:
        # Log the error and return empty list for now
        print(f"Error in list_workitems: {e}")
        return []

# Create a new work item
@app.post("/workitems", response_model=WorkItem)
async def create_workitem(item: WorkItem, admin: dict = Depends(require_admin_auth_cookie)):
    query = """
        INSERT INTO work_experience (portfolio_id, company, position, location, start_date, end_date, description, is_current, company_url, sort_order)
        VALUES (:portfolio_id, :company, :position, :location, :start_date, :end_date, :description, :is_current, :company_url, :sort_order)
        RETURNING *
    """
    row = await database.fetch_one(query, item.dict(exclude_unset=True))
    return WorkItem(**dict(row))

# Update a work item
@app.put("/workitems/{id}", response_model=WorkItem)
async def update_workitem(id: str, item: WorkItem, admin: dict = Depends(require_admin_auth_cookie)):
    query = """
        UPDATE work_experience SET
            company=:company, position=:position, location=:location, start_date=:start_date, end_date=:end_date,
            description=:description, is_current=:is_current, company_url=:company_url, sort_order=:sort_order
        WHERE id=:id RETURNING *
    """
    values = item.dict(exclude_unset=True)
    values["id"] = id
    row = await database.fetch_one(query, values)
    if not row:
        raise HTTPException(status_code=404, detail="Work item not found")
    return WorkItem(**dict(row))

# Delete a work item
@app.delete("/workitems/{id}")
async def delete_workitem(id: str, admin: dict = Depends(require_admin_auth_cookie)):
    query = "DELETE FROM work_experience WHERE id=:id"
    result = await database.execute(query, {"id": id})
    return {"success": True}


# --- Bulk Operations for Work Items ---

@app.post("/workitems/bulk", response_model=BulkWorkItemsResponse)
async def bulk_create_update_workitems(request: BulkWorkItemsRequest, admin: dict = Depends(require_admin_auth_cookie)):
    """
    Bulk create or update work items. 
    Items with existing IDs will be updated, items without IDs will be created.
    """
    created = []
    updated = []
    errors = []
    
    for item in request.items:
        try:
            # Validate required fields
            if not item.company or not item.company.strip():
                raise ValueError("Company name is required")
            if not item.position or not item.position.strip():
                raise ValueError("Position is required")
            if not item.start_date or not item.start_date.strip():
                raise ValueError("Start date is required")
                
            if item.id:
                # Update existing item
                query = """
                    UPDATE work_experience SET
                        company=:company, position=:position, location=:location, 
                        start_date=:start_date, end_date=:end_date,
                        description=:description, is_current=:is_current, 
                        company_url=:company_url, sort_order=:sort_order
                    WHERE id=:id RETURNING *
                """
                values = {
                    "company": item.company,
                    "position": item.position,
                    "location": item.location,
                    "start_date": item.start_date,
                    "end_date": item.end_date,
                    "description": item.description,
                    "is_current": item.is_current,
                    "company_url": item.company_url,
                    "sort_order": item.sort_order,
                    "id": item.id
                }
                row = await database.fetch_one(query, values)
                if row:
                    updated.append(WorkItem(**dict(row)))
                else:
                    errors.append({
                        "item": item.dict(),
                        "error": f"Work item with id {item.id} not found"
                    })
            else:
                # Create new item
                query = """
                    INSERT INTO work_experience 
                    (portfolio_id, company, position, location, start_date, 
                     end_date, description, is_current, company_url, sort_order)
                    VALUES (:portfolio_id, :company, :position, :location, 
                            :start_date, :end_date, :description, :is_current, 
                            :company_url, :sort_order)
                    RETURNING *
                """
                values = item.dict(exclude_unset=True)
                # Set default portfolio_id for new items
                values["portfolio_id"] = "daniel-blackburn"
                row = await database.fetch_one(query, values)
                created.append(WorkItem(**dict(row)))
                
        except Exception as e:
            # Detailed error logging for debugging
            error_msg = str(e)
            if hasattr(item, 'id') and item.id:
                log_msg = f"Failed to update item ID {item.id}: {error_msg}"
            else:
                log_msg = f"Failed to create new item: {error_msg}"
            
            logging.error(f"Bulk operation error: {log_msg}")
            errors.append({
                "item": item.dict() if hasattr(item, 'dict') else str(item),
                "error": error_msg
            })
    
    return BulkWorkItemsResponse(
        created=created,
        updated=updated,
        errors=errors
    )


@app.delete("/workitems/bulk", response_model=BulkDeleteResponse)
async def bulk_delete_workitems(request: BulkDeleteRequest, admin: dict = Depends(require_admin_auth_cookie)):
    """
    Bulk delete work items by their IDs.
    """
    deleted_count = 0
    errors = []
    
    for item_id in request.ids:
        try:
            query = "DELETE FROM work_experience WHERE id=:id"
            result = await database.execute(query, {"id": item_id})
            if result:
                deleted_count += 1
            else:
                errors.append({
                    "id": item_id,
                    "error": "Work item not found or already deleted"
                })
        except Exception as e:
            errors.append({
                "id": item_id,
                "error": str(e)
            })
    
    return BulkDeleteResponse(
        deleted_count=deleted_count,
        errors=errors
    )


# --- CRUD Endpoints for Projects ---

# List all projects
@app.get("/projects", response_model=List[Project])
async def list_projects():
    if not DATABASE_AVAILABLE:
        # Return sample data for testing
        return [
            Project(
                id="sample-1",
                portfolio_id="daniel-blackburn",
                title="Sample Project",
                description="A sample project for testing",
                url="https://github.com/example/project",
                image_url="https://via.placeholder.com/300x200",
                technologies=["Python", "FastAPI", "React"],
                sort_order=1
            )
        ]
    
    try:
        # First check if table exists
        check_table = "SELECT to_regclass('projects')"
        table_exists = await database.fetch_val(check_table)
        
        if not table_exists:
            # Return empty list if table doesn't exist
            return []
            
        query = "SELECT * FROM projects ORDER BY sort_order, title"
        rows = await database.fetch_all(query)
        
        # Convert rows to Project objects, handling any missing fields
        projects = []
        for row in rows:
            row_dict = dict(row)
            # Handle JSON field for technologies
            technologies = row_dict.get("technologies", [])
            if isinstance(technologies, str):
                try:
                    technologies = json.loads(technologies)
                except (json.JSONDecodeError, TypeError):
                    technologies = []
            
            project = Project(
                id=str(row_dict["id"]),
                portfolio_id=row_dict.get("portfolio_id", "daniel-blackburn"),
                title=row_dict.get("title", ""),
                description=row_dict.get("description", ""),
                url=row_dict.get("url"),
                image_url=row_dict.get("image_url"),
                technologies=technologies,
                sort_order=row_dict.get("sort_order", 0)
            )
            projects.append(project)
        
        return projects
    except Exception as e:
        print(f"Error fetching projects: {e}")
        return []


# Create a new project
@app.post("/projects", response_model=Project)
async def create_project(project: Project, admin: dict = Depends(require_admin_auth_cookie)):
    query = """
        INSERT INTO projects (portfolio_id, title, description, url, image_url, technologies, sort_order)
        VALUES (:portfolio_id, :title, :description, :url, :image_url, :technologies, :sort_order)
        RETURNING *
    """
    
    technologies_json = json.dumps(project.technologies or [])
    
    row = await database.fetch_one(query, {
        "portfolio_id": project.portfolio_id,
        "title": project.title,
        "description": project.description,
        "url": project.url,
        "image_url": project.image_url,
        "technologies": technologies_json,
        "sort_order": project.sort_order
    })
    # Handle JSON field for technologies
    row_dict = dict(row)
    technologies = row_dict.get("technologies", [])
    if isinstance(technologies, str):
        try:
            technologies = json.loads(technologies)
        except (json.JSONDecodeError, TypeError):
            technologies = []
    
    return Project(
        id=str(row_dict["id"]),
        portfolio_id=row_dict.get("portfolio_id", "daniel-blackburn"),
        title=row_dict.get("title", ""),
        description=row_dict.get("description", ""),
        url=row_dict.get("url"),
        image_url=row_dict.get("image_url"),
        technologies=technologies,
        sort_order=row_dict.get("sort_order", 0)
    )


# Update a project
@app.put("/projects/{id}", response_model=Project)
async def update_project(id: str, project: Project, admin: dict = Depends(require_admin_auth_cookie)):
    query = """
        UPDATE projects SET
            title=:title, description=:description, url=:url, image_url=:image_url,
            technologies=:technologies, sort_order=:sort_order
        WHERE id=:id
        RETURNING *
    """
    
    technologies_json = json.dumps(project.technologies or [])
    
    row = await database.fetch_one(query, {
        "id": id,
        "title": project.title,
        "description": project.description,
        "url": project.url,
        "image_url": project.image_url,
        "technologies": technologies_json,
        "sort_order": project.sort_order
    })
    if not row:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Handle JSON field for technologies
    row_dict = dict(row)
    technologies = row_dict.get("technologies", [])
    if isinstance(technologies, str):
        try:
            technologies = json.loads(technologies)
        except (json.JSONDecodeError, TypeError):
            technologies = []
    
    return Project(
        id=str(row_dict["id"]),
        portfolio_id=row_dict.get("portfolio_id", "daniel-blackburn"),
        title=row_dict.get("title", ""),
        description=row_dict.get("description", ""),
        url=row_dict.get("url"),
        image_url=row_dict.get("image_url"),
        technologies=technologies,
        sort_order=row_dict.get("sort_order", 0)
    )


# Delete a project
@app.delete("/projects/{id}")
async def delete_project(id: str, admin: dict = Depends(require_admin_auth_cookie)):
    query = "DELETE FROM projects WHERE id=:id"
    result = await database.execute(query, {"id": id})
    return {"deleted": True, "id": id}


# Bulk create/update projects
@app.post("/projects/bulk", response_model=BulkProjectsResponse)
async def bulk_create_update_projects(request: BulkProjectsRequest, admin: dict = Depends(require_admin_auth_cookie)):
    """
    Bulk create or update projects.
    """
    created = []
    updated = []
    errors = []
    
    for project in request.items:
        try:
            if project.id:
                # Update existing project
                query = """
                    UPDATE projects SET
                        title=:title, description=:description, url=:url,
                        image_url=:image_url, technologies=:technologies,
                        sort_order=:sort_order
                    WHERE id=:id
                    RETURNING *
                """
                
                technologies_json = json.dumps(project.technologies or [])
                
                row = await database.fetch_one(query, {
                    "id": project.id,
                    "title": project.title,
                    "description": project.description,
                    "url": project.url,
                    "image_url": project.image_url,
                    "technologies": technologies_json,
                    "sort_order": project.sort_order
                })
                if row:
                    # Handle JSON field for technologies
                    row_dict = dict(row)
                    technologies = row_dict.get("technologies", [])
                    if isinstance(technologies, str):
                        try:
                            technologies = json.loads(technologies)
                        except (json.JSONDecodeError, TypeError):
                            technologies = []
                    
                    updated_project = Project(
                        id=str(row_dict["id"]),
                        portfolio_id=row_dict.get("portfolio_id", "daniel-blackburn"),
                        title=row_dict.get("title", ""),
                        description=row_dict.get("description", ""),
                        url=row_dict.get("url"),
                        image_url=row_dict.get("image_url"),
                        technologies=technologies,
                        sort_order=row_dict.get("sort_order", 0)
                    )
                    updated.append(updated_project)
                else:
                    errors.append({
                        "project": project.dict() if hasattr(project, 'dict') else str(project),
                        "error": f"Project with id {project.id} not found"
                    })
            else:
                # Create new project
                query = """
                    INSERT INTO projects (portfolio_id, title, description, url, image_url, technologies, sort_order)
                    VALUES (:portfolio_id, :title, :description, :url, :image_url, :technologies, :sort_order)
                    RETURNING *
                """
                
                technologies_json = json.dumps(project.technologies or [])
                
                row = await database.fetch_one(query, {
                    "portfolio_id": project.portfolio_id,
                    "title": project.title,
                    "description": project.description,
                    "url": project.url,
                    "image_url": project.image_url,
                    "technologies": technologies_json,
                    "sort_order": project.sort_order
                })
                # Handle JSON field for technologies
                row_dict = dict(row)
                technologies = row_dict.get("technologies", [])
                if isinstance(technologies, str):
                    try:
                        technologies = json.loads(technologies)
                    except (json.JSONDecodeError, TypeError):
                        technologies = []
                
                created_project = Project(
                    id=str(row_dict["id"]),
                    portfolio_id=row_dict.get("portfolio_id", "daniel-blackburn"),
                    title=row_dict.get("title", ""),
                    description=row_dict.get("description", ""),
                    url=row_dict.get("url"),
                    image_url=row_dict.get("image_url"),
                    technologies=technologies,
                    sort_order=row_dict.get("sort_order", 0)
                )
                created.append(created_project)
        except Exception as e:
            errors.append({
                "project": project.dict() if hasattr(project, 'dict') else str(project),
                "error": str(e)
            })
    
    return BulkProjectsResponse(
        created=created,
        updated=updated,
        errors=errors
    )


# Bulk delete projects
@app.delete("/projects/bulk", response_model=BulkDeleteResponse)
async def bulk_delete_projects(request: BulkDeleteRequest, admin: dict = Depends(require_admin_auth_cookie)):
    """
    Bulk delete projects by their IDs.
    """
    deleted_count = 0
    errors = []
    
    for item_id in request.ids:
        try:
            query = "DELETE FROM projects WHERE id=:id"
            result = await database.execute(query, {"id": item_id})
            if result:
                deleted_count += 1
            else:
                errors.append({
                    "id": item_id,
                    "error": "Project not found or already deleted"
                })
        except Exception as e:
            errors.append({
                "id": item_id,
                "error": str(e)
            })
    
    return BulkDeleteResponse(
        deleted_count=deleted_count,
        errors=errors
    )


# API health check
@app.get("/health")
async def health_check():
    try:
        # Test database connection
        result = await database.fetch_one("SELECT 1")
        return {"status": "healthy", "database": "connected", "result": result}
    except Exception as e:
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}

# Debug endpoint to check work_experience table
@app.get("/debug/tables")
async def debug_tables():
    try:
        # Check if work_experience table exists
        tables_query = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        ORDER BY table_name
        """
        tables = await database.fetch_all(tables_query)
        
        work_experience_exists = any(row['table_name'] == 'work_experience' for row in tables)
        
        result = {
            "all_tables": [row['table_name'] for row in tables],
            "work_experience_exists": work_experience_exists
        }
        
        if work_experience_exists:
            # Get column info for work_experience
            columns_query = """
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = 'work_experience'
            ORDER BY ordinal_position
            """
            columns = await database.fetch_all(columns_query)
            result["work_experience_columns"] = [
                {
                    "name": row['column_name'], 
                    "type": row['data_type'],
                    "nullable": row['is_nullable']
                } 
                for row in columns
            ]
            
            # Get count
            count_result = await database.fetch_one("SELECT COUNT(*) as count FROM work_experience")
            result["work_experience_count"] = count_result['count'] if count_result else 0
        
        return result
        
    except Exception as e:
        return {"error": str(e)}

@app.get("/schema")
async def get_database_schema():
    """Return database schema information with table details, column info, and record counts"""
    try:
        # Get all tables in the public schema
        tables_query = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        ORDER BY table_name
        """
        tables = await database.fetch_all(tables_query)
        
        schema_info = {}
        
        for table_row in tables:
            table_name = table_row['table_name']
            
            # Get column information for each table
            columns_query = """
            SELECT 
                column_name, 
                data_type, 
                is_nullable, 
                column_default,
                character_maximum_length
            FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = :table_name
            ORDER BY ordinal_position
            """
            columns = await database.fetch_all(columns_query, {"table_name": table_name})
            
            # Get record count for each table
            count_query = f"SELECT COUNT(*) as count FROM {table_name}"
            count_result = await database.fetch_one(count_query)
            record_count = count_result['count'] if count_result else 0
            
            # Format column information
            column_info = []
            for col in columns:
                column_detail = {
                    "name": col['column_name'],
                    "type": col['data_type'],
                    "nullable": col['is_nullable'] == 'YES',
                    "default": col['column_default'],
                }
                if col['character_maximum_length']:
                    column_detail["max_length"] = col['character_maximum_length']
                column_info.append(column_detail)
            
            schema_info[table_name] = {
                "columns": column_info,
                "record_count": record_count
            }
        
        return {
            "database_schema": schema_info,
            "tables_count": len(tables),
            "generated_at": "2025-01-01T00:00:00Z"  # Static timestamp for testing
        }
        
    except Exception as e:
        return {"error": f"Failed to retrieve schema: {str(e)}", "schema": {}}

# GraphQL Playground (development only)
@app.get("/playground", response_class=HTMLResponse)
async def graphql_playground():
    """Serve GraphQL Playground for development"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>GraphQL Playground</title>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/graphql-playground-react/build/static/css/index.css" />
        <link rel="shortcut icon" href="https://cdn.jsdelivr.net/npm/graphql-playground-react/build/favicon.png" />
    </head>
    <body>
        <div id="root"></div>
        <script>
            window.addEventListener('load', function (event) {
                GraphQLPlayground.init(document.getElementById('root'), {
                    endpoint: '/graphql'
                })
            })
        </script>
        <script src="https://cdn.jsdelivr.net/npm/graphql-playground-react/build/static/js/middleware.js"></script>
    </body>
    </html>
    """


@app.get("/debug/oauth-status")
async def debug_oauth_status():
    """Debug endpoint to check OAuth configuration"""
    import os

    current_domain = ("www.blackburnsystems.com"
                      if os.getenv("ENV") == "production"
                      else "localhost:8000")

    status_info = {
        "oauth_configured": bool(oauth and oauth.google),
        "google_client_id_set": bool(os.getenv("GOOGLE_CLIENT_ID")),
        "google_client_secret_set": bool(os.getenv("GOOGLE_CLIENT_SECRET")),
        "google_redirect_uri": os.getenv("GOOGLE_REDIRECT_URI", "Not set"),
        "authorized_emails_set": bool(os.getenv("AUTHORIZED_EMAILS")),
        "secret_key_set": bool(os.getenv("SECRET_KEY")),
        "environment": os.getenv("ENV", "development"),
        "current_domain": current_domain
    }

    # Add partial client ID for verification (first 10 chars)
    client_id = os.getenv("GOOGLE_CLIENT_ID", "")
    if client_id:
        preview = (f"{client_id[:15]}..."
                   if len(client_id) > 15
                   else client_id)
        status_info["client_id_preview"] = preview

    return JSONResponse(content=status_info)


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
