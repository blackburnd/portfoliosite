# main.py - Lightweight FastAPI application with GraphQL and Google OAuth
import os
import secrets
import logging
import time
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
    require_admin_auth,
    create_user_session,
    create_access_token
)
from cookie_auth import require_admin_auth_cookie
from linkedin_sync import linkedin_sync, LinkedInSyncError

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
        result = await google.authorize_redirect(
            request, 
            redirect_uri,
            state=state
        )
        
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
        response = RedirectResponse(url="/admin/work/")
        response.set_cookie(
            key="access_token", 
            value=f"Bearer {access_token}",
            httponly=True,
            secure=False,  # Set to True in production with HTTPS
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
        "user_email": user_email
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
        "user_email": user_email
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
async def work_admin_page(request: Request, admin: dict = Depends(require_admin_auth)):
    return templates.TemplateResponse("workadmin.html", {
        "request": request,
        "current_page": "workadmin",
        "user": admin
    })


@app.get("/workadmin/bulk", response_class=HTMLResponse)
async def work_admin_bulk_page(request: Request, admin: dict = Depends(require_admin_auth)):
    """New bulk editor interface for work items"""
    return templates.TemplateResponse("workadmin_bulk.html", {
        "request": request,
        "current_page": "workadmin_bulk",
        "user": admin
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
        "user": {"email": "debug@example.com", "name": "Debug User"}  # Mock user for template
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
async def projects_admin_page(request: Request, admin: dict = Depends(require_admin_auth)):
    return templates.TemplateResponse("projectsadmin.html", {
        "request": request,
        "current_page": "projectsadmin",
        "user": admin
    })


@app.get("/projectsadmin/bulk", response_class=HTMLResponse)
async def projects_admin_bulk_page(request: Request, admin: dict = Depends(require_admin_auth)):
    """New bulk editor interface for projects"""
    return templates.TemplateResponse("projectsadmin_bulk.html", {
        "request": request,
        "current_page": "projectsadmin_bulk",
        "user": admin
    })


@app.get("/linkedin", response_class=HTMLResponse)
async def linkedin_admin_page(request: Request, admin: dict = Depends(require_admin_auth_cookie)):
    """LinkedIn sync admin interface"""
    return templates.TemplateResponse("linkedin_admin.html", {
        "request": request,
        "current_page": "linkedin_admin",
        "user": admin
    })


# --- LinkedIn Sync Admin Endpoints ---

@app.get("/linkedin/status")
async def linkedin_sync_status(admin: dict = Depends(require_admin_auth)):
    """Get LinkedIn sync configuration status"""
    try:
        status = linkedin_sync.get_sync_status()
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


@app.post("/linkedin/sync/profile")
async def sync_linkedin_profile(admin: dict = Depends(require_admin_auth)):
    """Sync LinkedIn profile data to portfolio"""
    try:
        logger.info(f"LinkedIn profile sync initiated by user: {admin.get('email', 'unknown')}")
        result = await linkedin_sync.sync_profile_data()
        return JSONResponse({
            "status": "success",
            "result": result
        })
    except LinkedInSyncError as e:
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
async def sync_linkedin_experience(admin: dict = Depends(require_admin_auth)):
    """Sync LinkedIn work experience data to database"""
    try:
        logger.info(f"LinkedIn experience sync initiated by user: {admin.get('email', 'unknown')}")
        result = await linkedin_sync.sync_experience_data()
        return JSONResponse({
            "status": "success",
            "result": result
        })
    except LinkedInSyncError as e:
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
async def sync_linkedin_full(admin: dict = Depends(require_admin_auth)):
    """Perform full LinkedIn sync (profile + experience)"""
    try:
        logger.info(f"Full LinkedIn sync initiated by user: {admin.get('email', 'unknown')}")
        result = await linkedin_sync.full_sync()
        return JSONResponse({
            "status": "success",
            "result": result
        })
    except LinkedInSyncError as e:
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
        # First check if table exists
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
async def create_workitem(item: WorkItem, admin: dict = Depends(require_admin_auth)):
    query = """
        INSERT INTO work_experience (portfolio_id, company, position, location, start_date, end_date, description, is_current, company_url, sort_order)
        VALUES (:portfolio_id, :company, :position, :location, :start_date, :end_date, :description, :is_current, :company_url, :sort_order)
        RETURNING *
    """
    row = await database.fetch_one(query, item.dict(exclude_unset=True))
    return WorkItem(**dict(row))

# Update a work item
@app.put("/workitems/{id}", response_model=WorkItem)
async def update_workitem(id: str, item: WorkItem, admin: dict = Depends(require_admin_auth)):
    query = """
        UPDATE work_experience SET
            company=:company, position=:position, location=:location, start_date=:start_date, end_date=:end_date,
            description=:description, is_current=:is_current, company_url=:company_url, sort_order=:sort_order, updated_at=NOW()
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
async def delete_workitem(id: str, admin: dict = Depends(require_admin_auth)):
    query = "DELETE FROM work_experience WHERE id=:id"
    result = await database.execute(query, {"id": id})
    return {"success": True}


# --- Bulk Operations for Work Items ---

@app.post("/workitems/bulk", response_model=BulkWorkItemsResponse)
async def bulk_create_update_workitems(request: BulkWorkItemsRequest, admin: dict = Depends(require_admin_auth)):
    """
    Bulk create or update work items. 
    Items with existing IDs will be updated, items without IDs will be created.
    """
    created = []
    updated = []
    errors = []
    
    for item in request.items:
        try:
            if item.id:
                # Update existing item
                query = """
                    UPDATE work_experience SET
                        company=:company, position=:position, location=:location, 
                        start_date=:start_date, end_date=:end_date,
                        description=:description, is_current=:is_current, 
                        company_url=:company_url, sort_order=:sort_order, 
                        updated_at=NOW()
                    WHERE id=:id RETURNING *
                """
                values = item.dict(exclude_unset=True)
                values["id"] = item.id
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
                row = await database.fetch_one(query, item.dict(exclude_unset=True))
                created.append(WorkItem(**dict(row)))
                
        except Exception as e:
            errors.append({
                "item": item.dict(),
                "error": str(e)
            })
    
    return BulkWorkItemsResponse(
        created=created,
        updated=updated,
        errors=errors
    )


@app.delete("/workitems/bulk", response_model=BulkDeleteResponse)
async def bulk_delete_workitems(request: BulkDeleteRequest, admin: dict = Depends(require_admin_auth)):
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
async def create_project(project: Project, admin: dict = Depends(require_admin_auth)):
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
    return Project(**dict(row))


# Update a project
@app.put("/projects/{id}", response_model=Project)
async def update_project(id: str, project: Project, admin: dict = Depends(require_admin_auth)):
    query = """
        UPDATE projects SET
            title=:title, description=:description, url=:url, image_url=:image_url,
            technologies=:technologies, sort_order=:sort_order, updated_at=NOW()
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
    return Project(**dict(row))


# Delete a project
@app.delete("/projects/{id}")
async def delete_project(id: str, admin: dict = Depends(require_admin_auth)):
    query = "DELETE FROM projects WHERE id=:id"
    result = await database.execute(query, {"id": id})
    return {"deleted": True, "id": id}


# Bulk create/update projects
@app.post("/projects/bulk", response_model=BulkProjectsResponse)
async def bulk_create_update_projects(request: BulkProjectsRequest, admin: dict = Depends(require_admin_auth)):
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
                        sort_order=:sort_order, updated_at=NOW()
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
                updated.append(Project(**dict(row)))
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
                created.append(Project(**dict(row)))
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
async def bulk_delete_projects(request: BulkDeleteRequest, admin: dict = Depends(require_admin_auth)):
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

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
