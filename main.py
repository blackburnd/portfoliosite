# main.py - Lightweight FastAPI application with GraphQL and Google OAuth
# Restored to working state - ce98ca2 with full CRUD functionality
import os
import secrets
import logging
import time
import traceback
import sys
import uuid
from datetime import datetime
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException, Depends, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, Response, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
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
from log_capture import add_log

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
from ttw_oauth_manager import TTWOAuthManager, TTWOAuthManagerError
from ttw_linkedin_sync import TTWLinkedInSync, TTWLinkedInSyncError

# Session-based authentication dependency
async def require_admin_auth_session(request: Request):
    """Require admin authentication via session"""
    if not hasattr(request, 'session') or 'user' not in request.session:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Please log in."
        )
    
    user_session = request.session.get('user', {})
    if not user_session.get('authenticated') or not user_session.get('is_admin'):
        raise HTTPException(
            status_code=403,
            detail="Admin access required."
        )
    
    return user_session

from app.resolvers import schema
from database import init_database, close_database, database
from databases import Database

# Pydantic model for work item
class WorkItem(BaseModel):
    id: Optional[str] = None
    portfolio_id: str
    company: str
    position: str
    location: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    description: Optional[str] = None
    is_current: Optional[bool] = False
    company_url: Optional[str] = None
    sort_order: Optional[int] = 0


# Pydantic model for project
class Project(BaseModel):
    id: Optional[str] = None
    portfolio_id: str = "daniel-blackburn"
    title: str
    description: str
    url: Optional[str] = None
    image_url: Optional[str] = None
    technologies: Optional[List[str]] = []
    sort_order: Optional[int] = 0


# Pydantic model for contact message
class ContactMessage(BaseModel):
    id: Optional[str] = None
    name: str
    email: str
    subject: Optional[str] = None
    message: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    submitted_at: Optional[str] = None
    is_read: Optional[bool] = False
    admin_notes: Optional[str] = None


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

# Global Exception Handlers for Error Logging and Clean Error Pages

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler to log all unhandled errors with tracebacks"""
    
    # Generate detailed error information
    error_id = secrets.token_urlsafe(8)
    error_time = datetime.now().isoformat()
    error_type = type(exc).__name__
    error_message = str(exc)
    error_traceback = traceback.format_exc()
    
    # Log the complete error details
    logger.error(f"UNHANDLED EXCEPTION [{error_id}] at {error_time}")
    logger.error(f"Error Type: {error_type}")
    logger.error(f"Error Message: {error_message}")
    logger.error(f"Request URL: {request.url}")
    logger.error(f"Request Method: {request.method}")
    logger.error(f"Request Headers: {dict(request.headers)}")
    logger.error(f"Full Traceback:\n{error_traceback}")
    
    # Add to database log if possible
    try:
        # Format the traceback and error details for the database log
        detailed_message = f"""[{error_id}] {error_type}: {error_message}
URL: {request.url} | Method: {request.method}
Headers: {dict(request.headers)}
Full Traceback:
{error_traceback}"""
        
        # Build extra data for the log entry
        extra_data = {
            "error_id": error_id,
            "error_type": error_type,
            "request_url": str(request.url),
            "request_method": request.method,
            "request_headers": dict(request.headers)
        }
        
        add_log(
            "ERROR",
            "global_exception_handler",
            detailed_message,
            function="global_exception_handler",
            line=0,
            user=None,
            extra=extra_data
        )
    except Exception as log_error:
        logger.error(f"Failed to log exception to database: {log_error}")
    
    # Return clean error page for HTML requests, JSON for API requests
    if "text/html" in request.headers.get("accept", ""):
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error_id": error_id,
                "error_type": error_type,
                "error_message": "An unexpected error occurred. The technical team has been notified.",
                "is_production": os.getenv("ENV") == "production"
            },
            status_code=500
        )
    else:
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "error_id": error_id,
                "message": "An unexpected error occurred. Please try again later.",
                "timestamp": error_time
            }
        )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with logging"""
    
    error_id = secrets.token_urlsafe(8)
    
    # Log HTTP exceptions
    logger.warning(f"HTTP EXCEPTION [{error_id}]: {exc.status_code} - {exc.detail} | URL: {request.url}")
    
    # Add to database log
    try:
        add_log(
            "WARNING",
            "http_exception",
            f"[{error_id}] {exc.status_code}: {exc.detail} | URL: {request.url}",
            error_id=error_id,
            status_code=exc.status_code,
            request_url=str(request.url),
            request_method=request.method
        )
    except Exception as log_error:
        logger.error(f"Failed to log HTTP exception to database: {log_error}")
    
    # Return clean error page for HTML requests
    if "text/html" in request.headers.get("accept", ""):
        # Special handling for 404s
        if exc.status_code == 404:
            return templates.TemplateResponse(
                "404.html",
                {"request": request, "error_id": error_id},
                status_code=404
            )
        
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error_id": error_id,
                "error_type": f"HTTP {exc.status_code}",
                "error_message": exc.detail,
                "is_production": os.getenv("ENV") == "production"
            },
            status_code=exc.status_code
        )
    else:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.detail,
                "error_id": error_id,
                "status_code": exc.status_code
            }
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

# Log OAuth configuration from database
@app.on_event("startup")
async def check_oauth_configuration():
    """Check OAuth configuration from database on startup"""
    try:
        ttw_manager = TTWOAuthManager()
        google_configured = await ttw_manager.is_google_oauth_app_configured()
        linkedin_configured = await ttw_manager.is_oauth_app_configured()
        
        logger.info(f"Google OAuth configured: {google_configured}")
        logger.info(f"LinkedIn OAuth configured: {linkedin_configured}")
        
        if google_configured:
            config = await ttw_manager.get_google_oauth_app_config()
            if config:
                logger.info(f"Google OAuth redirect URI: {config.get('redirect_uri')}")
        
        if not google_configured and not linkedin_configured:
            logger.warning("No OAuth providers configured - check admin interface")
            
    except Exception as e:
        logger.error(f"Failed to check OAuth configuration: {e}")

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
app.mount("/assets", BrowsableStaticFiles(directory="assets"), name="static")
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
        logger.info("Initializing database connection...")
        await init_database()
        logger.info("Database initialized successfully")
        
        # Database logging is now handled directly by add_log function
        logger.info("Database logging ready via add_log function")
    except Exception as e:
        logger.error(f"Startup error: {str(e)}", exc_info=True)
        raise


@app.on_event("shutdown")
async def shutdown_event():
    await close_database()


# --- Google OAuth Authentication Routes ---

@app.get("/auth/login")
async def auth_login(request: Request):
    """Initiate Google OAuth login"""
    try:
        logger.info("=== OAuth Login Request Started ===")
        
        # Add log entry for login attempt
        add_log(
            level="INFO",
            source="auth",
            message="User initiated Google OAuth login process",
            module="auth",
            function="auth_login",
            extra=json.dumps({
                "ip_address": request.client.host if request.client else "unknown",
                "user_agent": request.headers.get("user-agent", "unknown")
            })
        )
        
        # Check if OAuth is properly configured
        if not oauth or not oauth.google:
            logger.error("OAuth not configured - missing credentials")
            add_log(
                level="ERROR",
                source="auth",
                message="OAuth login failed - missing Google OAuth configuration",
                module="auth",
                function="auth_login",
                extra=json.dumps({"reason": "missing_oauth_config"})
            )
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
            add_log(
                level="WARNING",
                source="auth",
                message=f"Unauthorized login attempt by {email}",
                user=email,
                module="auth",
                function="auth_callback",
                extra=json.dumps({
                    "email": email,
                    "reason": "not_authorized",
                    "ip_address": request.client.host if request.client else "unknown"
                })
            )
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
        
        # Store user data in session only (no JWT)
        request.session['user'] = {
            'email': email,
            'name': user_info.get('name', 'Unknown'),
            'access_token': token.get('access_token'),
            'refresh_token': token.get('refresh_token'),
            'token_expires_at': token.get('expires_at'),
            'authenticated': True,
            'is_admin': True  # Since they passed the admin check
        }
        
        # Log successful login and session creation
        add_log(
            level="INFO",
            source="auth",
            message=f"Successful login by {email} - session auth created",
            user=email,
            module="auth",
            function="auth_callback",
            extra=json.dumps({
                "email": email,
                "name": user_info.get('name', 'Unknown'),
                "ip_address": request.client.host if request.client else "unknown",
                "session_created": True,
                "auth_method": "session_only"
            })
        )
        
        # Redirect to admin page
        response = RedirectResponse(url="/workadmin")
        
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
async def logout(request: Request, response: Response):
    """Log out the user by clearing session state"""
    try:
        logger.info("=== Session Logout Request ===")
        
        # Get user info from session before clearing
        user_email = "unknown"
        if hasattr(request, 'session') and 'user' in request.session:
            user_session = request.session.get('user', {})
            user_email = user_session.get('email', 'unknown')
        
        # Add log entry for logout
        add_log(
            level="INFO",
            source="auth",
            message=f"User logged out: {user_email}",
            user=user_email,
            module="auth",
            function="logout",
            extra=json.dumps({
                "ip_address": request.client.host if request.client else "unknown",
                "auth_method": "session_only"
            })
        )
        
        # Clear all session data
        request.session.clear()
        
        logger.info("Successfully cleared session data")
        return RedirectResponse(url="/", status_code=303)
    except Exception as e:
        logger.error(f"Logout error: {str(e)}", exc_info=True)
        return RedirectResponse(url="/", status_code=303)


@app.get("/auth/disconnect")
async def disconnect(request: Request, response: Response):
    """Complete disconnect - logout and revoke Google OAuth tokens"""
    try:
        logger.info("=== OAuth Complete Disconnect Request ===")
        
        # Try to get user info before clearing session
        user_email = "unknown"
        try:
            access_token = request.cookies.get("access_token")
            if access_token:
                token = access_token.replace("Bearer ", "")
                payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
                user_email = payload.get("email", "unknown")
        except:
            pass
        
        # Add log entry for disconnect
        add_log(
            level="INFO",
            source="auth",
            message=f"User disconnected (revoked tokens): {user_email}",
            user=user_email,
            module="auth",
            function="disconnect",
            extra=json.dumps({
                "ip_address": request.client.host if request.client else "unknown",
                "action": "revoke_tokens"
            })
        )
        
        # First try to revoke the Google token if we have one
        try:
            access_token = request.cookies.get("access_token")
            if access_token and oauth and oauth.google:
                # Try to revoke the token at Google
                import httpx
                revoke_url = f"https://oauth2.googleapis.com/revoke?token={access_token}"
                async with httpx.AsyncClient() as client:
                    response_revoke = await client.post(revoke_url)
                    if response_revoke.status_code == 200:
                        logger.info("Successfully revoked Google OAuth token")
                    else:
                        logger.warning(f"Token revocation returned status: {response_revoke.status_code}")
        except Exception as revoke_error:
            logger.warning(f"Could not revoke Google token: {revoke_error}")
        
        # Clear the authentication cookie
        response.delete_cookie(key="access_token", path="/")
        
        # Clear all session data to ensure clean state for re-authentication
        request.session.clear()
        
        # Also clear any potential session cookie variations
        response.delete_cookie(key="session", path="/")
        response.delete_cookie(key="oauth_state", path="/")
        
        logger.info("Successfully disconnected and cleared all authentication data")
        return RedirectResponse(url="/", status_code=303)
    except Exception as e:
        logger.error(f"Disconnect error: {str(e)}", exc_info=True)
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
    try:
        form = await request.form()
        
        # Extract form data
        name = form.get("name", "").strip()
        email = form.get("email", "").strip()
        subject = form.get("subject", "").strip()
        message = form.get("message", "").strip()
        
        # Basic validation
        if not name or not email or not message:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error", 
                    "message": "Name, email, and message are required."
                }
            )
        
        # Get client IP and user agent
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        
        # Create contact message object
        contact_data = ContactMessage(
            name=name,
            email=email,
            subject=subject if subject else None,
            message=message,
            ip_address=client_ip,
            user_agent=user_agent,
            status="new"
        )
        
        # Save to database with dedicated connection like logs endpoint
        DATABASE_URL = os.getenv("_DATABASE_URL") or os.getenv("DATABASE_URL")
        db = Database(DATABASE_URL)
        await db.connect()
        
        try:
            query = """
                INSERT INTO contact_messages 
                (name, email, subject, message, created_at, ip_address, 
                 user_agent, status)
                VALUES (:name, :email, :subject, :message, NOW(), 
                        :ip_address, :user_agent, :status)
                RETURNING id
            """
            result = await db.fetch_one(
                query,
                {
                    "name": contact_data.name,
                    "email": contact_data.email,
                    "subject": contact_data.subject,
                    "message": contact_data.message,
                    "ip_address": contact_data.ip_address,
                    "user_agent": contact_data.user_agent,
                    "status": contact_data.status
                }
            )
            
            contact_id = result['id'] if result else None
            
        finally:
            await db.disconnect()
        
        logger.info(f"Contact form submitted: ID {contact_id}, "
                   f"from {name} ({email})")
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "Thank you for your message! I'll get back to you soon."
            }
        )
        
    except Exception as e:
        error_id = str(uuid.uuid4())[:8]
        logger.error(f"CONTACT FORM ERROR [{error_id}]: {str(e)}")
        
        # Log to app_log table
        await add_log(
            level="ERROR",
            message=f"[{error_id}] Contact form submission failed: {str(e)}",
            details=f"Form data: name={name if 'name' in locals() else 'unknown'}, "
                   f"email={email if 'email' in locals() else 'unknown'}"
        )
        
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": "An error occurred while submitting your message. Please try again."
            }
        )

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

@app.get("/resume")
@app.get("/resume/")
async def resume():
    """Serve resume PDF directly for browser viewing"""
    return FileResponse(
        path="assets/files/danielblackburn.pdf",
        media_type="application/pdf",
        filename="danielblackburn.pdf",
        headers={"Content-Disposition": "inline; filename=danielblackburn.pdf"}
    )


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
    admin: dict = Depends(require_admin_auth_session)
):
    return templates.TemplateResponse("workadmin.html", {
        "request": request,
        "current_page": "workadmin",
        "user_info": admin,
        "user_authenticated": True,
        "user_email": admin.get("email", "")
    })


# --- Logs Admin Page ---
@app.get("/logs", response_class=HTMLResponse)
async def logs_admin_page(
    request: Request,
    admin: dict = Depends(require_admin_auth_cookie)
):
    """Application logs viewer interface"""
    return templates.TemplateResponse("logs.html", {
        "request": request,
        "current_page": "logs",
        "user_info": admin,
        "user_authenticated": True,
        "user_email": admin.get("email", ""),
        "cache_bust_version": str(int(time.time()))
    })


@app.get("/logs/data")
async def get_logs_data(
    request: Request,
    offset: int = 0,
    limit: int = 50,
    page: int = None,
    admin: dict = Depends(require_admin_auth_cookie)
):
    """Get log data for endless scrolling logs interface"""
    from datetime import datetime
    
    # Handle backward compatibility with page parameter
    if page is not None:
        offset = (page - 1) * limit
    
    def serialize_datetime(obj):
        """Convert datetime objects to JSON-serializable strings"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        return obj
    
    try:
        # Add a test log entry to ensure we have something to display
        add_log("INFO", "logs_endpoint", "Logs endpoint accessed for debugging")
        
        # Create our own database connection like add_log does
        DATABASE_URL = os.getenv("_DATABASE_URL") or os.getenv("DATABASE_URL")
        db = Database(DATABASE_URL)
        await db.connect()
        
        try:
            # Get logs with offset/limit for endless scrolling
            logs_query = """
                SELECT timestamp, level, message, module, function, line, user, extra
                FROM app_log 
                ORDER BY timestamp DESC 
                LIMIT :limit OFFSET :offset
            """
            
            logs = await db.fetch_all(logs_query, {"limit": limit, "offset": offset})
            
            # Debug: Log what we found
            add_log("DEBUG", "logs_endpoint", f"Found {len(logs)} logs in database")
            
            # Convert logs to dict and serialize datetime objects
            logs_data = []
            for log in logs:
                log_dict = {}
                for key, value in dict(log).items():
                    log_dict[key] = serialize_datetime(value)
                logs_data.append(log_dict)
            
            # Check if there are more logs
            has_more = len(logs_data) == limit
            
            return JSONResponse({
                "status": "success",
                "logs": logs_data,
                "has_more": has_more,
                "has_next": has_more,  # Backward compatibility - same as has_more
                "pagination": {
                    "page": (offset // limit) + 1,
                    "limit": limit,
                    "offset": offset,
                    "total": len(logs_data)
                }
            })
        finally:
            await db.disconnect()
        
    except Exception as e:
        logger.error(f"Error fetching logs: {str(e)}")
        logger.error(f"Error details: {type(e).__name__}: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        
        # Also log this error to database
        try:
            add_log("ERROR", "logs_endpoint",
                    f"Failed to fetch logs: {str(e)}", extra=str(e))
        except Exception:
            pass
            
        return JSONResponse({
            "status": "error",
            "message": f"Failed to fetch logs: {str(e)}",
            "logs": [],
            "pagination": {
                "page": 1,
                "limit": limit,
                "total": 0,
                "pages": 0
            }
        }, status_code=500)


@app.post("/logs/clear")
async def clear_logs(
    request: Request,
    admin: dict = Depends(require_admin_auth_cookie)
):
    """Clear all application logs"""
    admin_email = admin.get("email")
    
    try:
        # Log the clear action before clearing
        add_log(
            "INFO",
            "logs_admin",
            f"Admin {admin_email} cleared all application logs",
            function="clear_logs",
            line=0,
            user=admin_email,
            extra={}
        )
        
        # Clear all logs
        await database.execute("DELETE FROM app_log")
        
        return JSONResponse({
            "status": "success",
            "message": "All logs cleared successfully"
        })
        
    except Exception as e:
        logger.error(f"Error clearing logs: {str(e)}")
        return JSONResponse({
            "status": "error",
            "message": f"Failed to clear logs: {str(e)}"
        }, status_code=500)


# --- Redirect admin/logs to /logs for convenience ---
# --- SQL Admin Tool ---
@app.get("/admin/sql", response_class=HTMLResponse)
async def sql_admin_page(
    request: Request,
    admin: dict = Depends(require_admin_auth_cookie)
):
    """SQL Admin interface for executing database queries"""
    return templates.TemplateResponse("sql_admin.html", {
        "request": request,
        "current_page": "sql_admin",
        "user_info": admin,
        "user_authenticated": True,
        "user_email": admin.get("email", "")
    })


@app.post("/admin/sql/execute")
async def execute_sql(
    request: Request,
    admin: dict = Depends(require_admin_auth_cookie)
):
    """Execute SQL query against the database"""
    import time
    import json
    from datetime import datetime, date
    
    def serialize_datetime(obj):
        """Convert datetime and UUID objects to JSON-serializable strings"""
        import uuid
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, date):
            return obj.isoformat()
        elif isinstance(obj, uuid.UUID):
            return str(obj)
        return obj
    
    start_time = time.time()
    
    try:
        body = await request.json()
        query = body.get("query", "").strip()
        
        if not query:
            return JSONResponse({
                "status": "error",
                "message": "No query provided"
            }, status_code=400)
        
        # Log the SQL execution attempt
        logger.info(f"SQL Admin: User {admin.get('email')} executing query: {query[:100]}{'...' if len(query) > 100 else ''}")
        
        await database.connect()
        
        # Determine if this is a SELECT query or a modification query
        is_select = query.upper().strip().startswith('SELECT') or query.upper().strip().startswith('PRAGMA')
        
        # Add specific log entry for query history tracking
        add_log(
            level="INFO", 
            source="sql_admin", 
            message=f"SQL Query executed by {admin.get('email', 'unknown')}: {query[:200]}{'...' if len(query) > 200 else ''}", 
            user=admin.get('email', 'unknown'),
            module="sql_admin",
            function="execute_sql",
            extra=json.dumps({
                "query_type": "SELECT" if is_select else "MODIFY",
                "query_length": len(query),
                "user_email": admin.get('email', 'unknown')
            })
        )
        
        if is_select:
            # For SELECT queries, fetch results
            rows = await database.fetch_all(query)
            # Convert rows to dicts and serialize datetime objects
            rows_data = []
            for row in rows:
                row_dict = {}
                for key, value in dict(row).items():
                    row_dict[key] = serialize_datetime(value)
                rows_data.append(row_dict)
            
            execution_time = round((time.time() - start_time) * 1000, 2)
            
            return JSONResponse({
                "status": "success",
                "rows": rows_data,
                "columns": list(rows_data[0].keys()) if rows_data else [],
                "execution_time": execution_time,
                "message": f"Query executed successfully. {len(rows_data)} rows returned."
            })
        else:
            # For INSERT/UPDATE/DELETE queries, execute and return row count
            result = await database.execute(query)
            execution_time = round((time.time() - start_time) * 1000, 2)
            
            return JSONResponse({
                "status": "success",
                "rows": [],
                "execution_time": execution_time,
                "message": f"Query executed successfully. {result} rows affected." if result else "Query executed successfully."
            })
            
    except Exception as e:
        execution_time = round((time.time() - start_time) * 1000, 2)
        error_msg = str(e)
        
        # Log the error
        logger.error(f"SQL Admin: Error executing query for user {admin.get('email')}: {error_msg}")
        
        return JSONResponse({
            "status": "error",
            "message": error_msg,
            "execution_time": execution_time
        }, status_code=500)
    finally:
        try:
            await database.disconnect()
        except:
            pass


@app.get("/admin/sql/download-schema")
async def download_schema(admin: dict = Depends(require_admin_auth_cookie)):
    """Download the current database schema as a SQL dump file"""
    from datetime import datetime
    from schema_dump import generate_schema_dump
    
    admin_email = admin.get("email")
    
    try:
        add_log("INFO", "sql_admin_schema_download", f"Admin {admin_email} downloading database schema")
        
        # Use the new schema dump module
        schema_content = await generate_schema_dump()
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"database_schema_{timestamp}.sql"
        
        add_log("INFO", "sql_admin_schema_downloaded", f"Schema successfully downloaded by {admin_email}")
        
        # Return the schema as a downloadable file
        return Response(
            content=schema_content,
            media_type="application/sql",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Type": "application/sql; charset=utf-8"
            }
        )
        
    except Exception as e:
        logger.error(f"Error downloading schema: {str(e)}")
        add_log("ERROR", "sql_admin_schema_error", f"Schema download error for {admin_email}: {str(e)}")
        return JSONResponse({
            "status": "error",
            "message": f"Schema download failed: {str(e)}"
        }, status_code=500)


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


# --- Database Schema Setup Endpoint ---

@app.get("/admin/oauth-status")
async def get_oauth_status():
    """Show current OAuth configuration status - no auth required"""
    try:
        # Check oauth_apps table for all providers
        oauth_apps_query = """
            SELECT id, provider, app_name, client_id, redirect_uri, is_active, created_by, created_at
            FROM oauth_apps 
            ORDER BY provider, created_at DESC
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
            "oauth_apps": [dict(row) for row in oauth_apps],
            "system_settings": [dict(row) for row in system_settings],
            "total_oauth_apps": len(oauth_apps),
            "total_system_settings": len(system_settings)
        })
        
    except Exception as e:
        logger.error(f"Error getting OAuth status: {str(e)}")
        return JSONResponse({
            "status": "error",
            "error": str(e)
        }, status_code=500)


# --- CRUD Endpoints for Work Items ---

# List all work items
@app.get("/workitems", response_model=List[WorkItem])
async def list_workitems():
    try:
        # Query work experience directly
        add_log("DEBUG", "workitems", "Fetching work items from database")
        query = "SELECT * FROM work_experience ORDER BY sort_order, start_date DESC"
        rows = await database.fetch_all(query)
        add_log("DEBUG", "workitems", f"Found {len(rows)} work items in database")
        
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

# Get a single work item
@app.get("/workitems/{id}", response_model=WorkItem)
async def get_workitem(id: str, admin: dict = Depends(require_admin_auth_cookie)):
    query = "SELECT * FROM work_experience WHERE id=:id"
    row = await database.fetch_one(query, {"id": id})
    if not row:
        raise HTTPException(status_code=404, detail="Work item not found")
    # Convert UUID to string for Pydantic model
    row_dict = dict(row)
    if row_dict.get('id'):
        row_dict['id'] = str(row_dict['id'])
    return WorkItem(**row_dict)

# Create a new work item
@app.post("/workitems", response_model=WorkItem)
async def create_workitem(item: WorkItem, admin: dict = Depends(require_admin_auth_cookie)):
    query = """
        INSERT INTO work_experience (portfolio_id, company, position, location, start_date, end_date, description, is_current, company_url, sort_order)
        VALUES (:portfolio_id, :company, :position, :location, :start_date, :end_date, :description, :is_current, :company_url, :sort_order)
        RETURNING *
    """
    row = await database.fetch_one(query, item.dict(exclude_unset=True))
    # Convert UUID to string for Pydantic model
    row_dict = dict(row)
    if row_dict.get('id'):
        row_dict['id'] = str(row_dict['id'])
    return WorkItem(**row_dict)

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
    # Convert UUID to string for Pydantic model
    row_dict = dict(row)
    if row_dict.get('id'):
        row_dict['id'] = str(row_dict['id'])
    return WorkItem(**row_dict)

# Delete a work item
@app.delete("/workitems/{id}")
async def delete_workitem(id: str, admin: dict = Depends(require_admin_auth_cookie)):
    query = "DELETE FROM work_experience WHERE id=:id"
    result = await database.execute(query, {"id": id})
    return {"success": True}


# --- CRUD Endpoints for Projects ---

# List all projects
@app.get("/projects", response_model=List[Project])
async def list_projects():
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


# Get a single project by ID
@app.get("/projects/{id}", response_model=Project)
async def get_project(id: str, admin: dict = Depends(require_admin_auth_cookie)):
    query = "SELECT * FROM projects WHERE id = :id"
    row = await database.fetch_one(query, {"id": id})
    
    if not row:
        raise HTTPException(status_code=404, detail="Project not found")
    
    row_dict = dict(row)
    # Handle JSON field for technologies
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
    await database.execute(query, {"id": id})
    return {"deleted": True, "id": id}


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



# --- Google OAuth Admin Endpoints ---
@app.get("/admin/oauth/google/status")
async def google_oauth_status(admin: dict = Depends(require_admin_auth_cookie)):
    """Get Google OAuth configuration status"""
    admin_email = admin.get("email")
    
    try:
        add_log("INFO", "oauth_google_status", f"Admin {admin_email} checked Google OAuth status")
        
        # Placeholder for Google OAuth implementation
        return JSONResponse({
            "configured": False,
            "connected": False,
            "message": "Google OAuth not yet implemented",
            "scopes": []
        })
        
    except Exception as e:
        logger.error(f"Error getting Google OAuth status: {str(e)}")
        add_log("ERROR", "oauth_google_error", f"Failed to get Google OAuth status for {admin_email}: {str(e)}")
        return JSONResponse({
            "status": "error",
            "error": str(e)
        }, status_code=500)


@app.post("/admin/oauth/google/configure")
async def configure_google_oauth(request: Request, admin: dict = Depends(require_admin_auth_cookie)):
    """Configure Google OAuth application"""
    admin_email = admin.get("email")
    
    try:
        data = await request.json()
        add_log("INFO", "oauth_google_configure_attempt", f"Admin {admin_email} attempted to configure Google OAuth")
        
        # Placeholder for Google OAuth configuration
        return JSONResponse({
            "status": "error",
            "message": "Google OAuth configuration not yet implemented"
        }, status_code=501)
        
    except Exception as e:
        logger.error(f"Error configuring Google OAuth: {str(e)}")
        add_log("ERROR", "oauth_google_configure_error", f"Failed to configure Google OAuth for {admin_email}: {str(e)}")
        return JSONResponse({
            "status": "error",
            "error": str(e)
        }, status_code=500)


# --- LinkedIn OAuth Admin Endpoints ---

@app.get("/admin/oauth/linkedin/status")
async def linkedin_oauth_status(admin: dict = Depends(require_admin_auth_cookie)):
    """Get LinkedIn OAuth configuration and connection status"""
    admin_email = admin.get("email")
    
    try:
        add_log("INFO", "oauth_linkedin_status", f"Admin {admin_email} checked LinkedIn OAuth status")
        
        ttw_oauth_manager = TTWOAuthManager()
        
        app_configured = await ttw_oauth_manager.is_oauth_app_configured()
        app_config = await ttw_oauth_manager.get_oauth_app_config() if app_configured else None
        connected = await ttw_oauth_manager.is_linkedin_connected(admin_email)
        connection_data = await ttw_oauth_manager.get_linkedin_connection(admin_email) if connected else None
        available_scopes = await ttw_oauth_manager.get_available_scopes()
        
        return JSONResponse({
            "app_configured": app_configured,
            "connected": connected,
            "config": app_config,
            "connection": connection_data,
            "scopes": available_scopes
        })
        
    except Exception as e:
        logger.error(f"Error getting LinkedIn OAuth status: {str(e)}")
        add_log("ERROR", "oauth_linkedin_status_error", f"Failed to get LinkedIn OAuth status for {admin_email}: {str(e)}")
        return JSONResponse({
            "status": "error",
            "error": str(e)
        }, status_code=500)


@app.post("/admin/oauth/linkedin/configure")
async def configure_linkedin_oauth(request: Request, admin: dict = Depends(require_admin_auth_cookie)):
    """Configure LinkedIn OAuth application settings"""
    admin_email = admin.get("email")
    
    try:
        data = await request.json()
        add_log("INFO", "oauth_linkedin_configure_attempt", f"Admin {admin_email} attempting to configure LinkedIn OAuth app")
        
        required_fields = ["client_id", "client_secret", "redirect_uri"]
        missing_fields = [field for field in required_fields if not data.get(field)]
        
        if missing_fields:
            add_log("ERROR", "oauth_linkedin_configure_validation_error", f"Missing required fields for {admin_email}: {missing_fields}")
            return JSONResponse({
                "status": "error",
                "message": f"Missing required fields: {', '.join(missing_fields)}"
            }, status_code=400)
        
        ttw_oauth_manager = TTWOAuthManager()
        success = await ttw_oauth_manager.configure_oauth_app(admin_email, data)
        
        if success:
            add_log("INFO", "oauth_linkedin_configure_success", f"Admin {admin_email} successfully configured LinkedIn OAuth app")
            return JSONResponse({
                "status": "success",
                "message": "LinkedIn OAuth application configured successfully"
            })
        else:
            add_log("ERROR", "oauth_linkedin_configure_failure", f"Failed to configure LinkedIn OAuth app for {admin_email}")
            return JSONResponse({
                "status": "error",
                "message": "Failed to configure LinkedIn OAuth application"
            }, status_code=500)
        
    except Exception as e:
        logger.error(f"Error configuring LinkedIn OAuth: {str(e)}")
        add_log("ERROR", "oauth_linkedin_configure_error", f"Error configuring LinkedIn OAuth for {admin_email}: {str(e)}")
        return JSONResponse({
            "status": "error",
            "error": str(e)
        }, status_code=500)


@app.post("/admin/oauth/linkedin/connect")
async def linkedin_oauth_connect(request: Request, admin: dict = Depends(require_admin_auth_cookie)):
    """Initiate LinkedIn OAuth connection flow"""
    admin_email = admin.get("email")
    
    try:
        data = await request.json()
        requested_scopes = data.get("scopes", [])
        
        add_log("INFO", "oauth_linkedin_connect_attempt", f"Admin {admin_email} initiating LinkedIn OAuth connection with scopes: {requested_scopes}")
        
        ttw_oauth_manager = TTWOAuthManager()
        
        # Check if OAuth app is configured first
        if not await ttw_oauth_manager.is_oauth_app_configured():
            add_log("INFO", "oauth_linkedin_connect_not_configured", f"LinkedIn OAuth app not configured for {admin_email}")
            return JSONResponse({
                "status": "error",
                "message": "LinkedIn OAuth application must be configured before connecting"
            }, status_code=400)
        
        auth_url, state = await ttw_oauth_manager.get_linkedin_authorization_url(admin_email, requested_scopes)
        
        add_log("INFO", "oauth_linkedin_auth_url_generated", f"Generated LinkedIn auth URL for {admin_email}")
        
        return JSONResponse({
            "status": "success",
            "auth_url": auth_url,
            "state": state
        })
        
    except Exception as e:
        logger.error(f"Error initiating LinkedIn OAuth: {str(e)}")
        add_log("ERROR", "oauth_linkedin_connect_error", f"Error initiating LinkedIn OAuth for {admin_email}: {str(e)}")
        return JSONResponse({
            "status": "error",
            "error": str(e)
        }, status_code=500)


@app.post("/admin/oauth/linkedin/disconnect")
async def linkedin_oauth_disconnect_admin(admin: dict = Depends(require_admin_auth_cookie)):
    """Disconnect LinkedIn OAuth connection"""
    admin_email = admin.get("email")
    
    try:
        add_log("INFO", "oauth_linkedin_disconnect_attempt", f"Admin {admin_email} attempting to disconnect LinkedIn OAuth")
        
        ttw_oauth_manager = TTWOAuthManager()
        success = await ttw_oauth_manager.remove_linkedin_connection(admin_email)
        
        if success:
            add_log("INFO", "oauth_linkedin_disconnect_success", f"Admin {admin_email} successfully disconnected LinkedIn OAuth")
            return JSONResponse({
                "status": "success",
                "message": "LinkedIn OAuth connection removed successfully"
            })
        else:
            add_log("ERROR", "oauth_linkedin_disconnect_failure", f"Failed to disconnect LinkedIn OAuth for {admin_email}")
            return JSONResponse({
                "status": "error",
                "message": "Failed to remove LinkedIn OAuth connection"
            }, status_code=500)
        
    except Exception as e:
        logger.error(f"Error disconnecting LinkedIn OAuth: {str(e)}")
        add_log("ERROR", "oauth_linkedin_disconnect_error", f"Error disconnecting LinkedIn OAuth for {admin_email}: {str(e)}")
        return JSONResponse({
            "status": "error",
            "error": str(e)
        }, status_code=500)


@app.post("/admin/oauth/linkedin/test")
async def test_linkedin_oauth_connection(admin: dict = Depends(require_admin_auth_cookie)):
    """Test LinkedIn OAuth connection by making an API call"""
    admin_email = admin.get("email")
    
    try:
        add_log("INFO", "oauth_linkedin_test_attempt", f"Admin {admin_email} testing LinkedIn OAuth connection")
        
        from ttw_linkedin_sync import TTWLinkedInSync
        sync_service = TTWLinkedInSync(admin_email)
        
        # Test connection by getting profile info
        profile_data = await sync_service.get_linkedin_profile()
        
        if profile_data:
            add_log("INFO", "oauth_linkedin_test_success", f"LinkedIn OAuth test successful for {admin_email}")
            return JSONResponse({
                "status": "success",
                "message": "LinkedIn OAuth connection test successful",
                "profile": {
                    "name": profile_data.get("localizedFirstName", "") + " " + profile_data.get("localizedLastName", ""),
                    "id": profile_data.get("id"),
                    "profile_url": f"https://linkedin.com/in/{profile_data.get('vanityName', profile_data.get('id'))}"
                }
            })
        else:
            add_log("ERROR", "oauth_linkedin_test_failure", f"LinkedIn OAuth test failed for {admin_email} - no profile data")
            return JSONResponse({
                "status": "error",
                "message": "Failed to retrieve LinkedIn profile data"
            }, status_code=500)
        
    except Exception as e:
        logger.error(f"Error testing LinkedIn OAuth: {str(e)}")
        add_log("ERROR", "oauth_linkedin_test_error", f"Error testing LinkedIn OAuth for {admin_email}: {str(e)}")
        return JSONResponse({
            "status": "error",
            "error": str(e)
        }, status_code=500)


# --- Google OAuth Admin Routes ---
@app.get("/admin/google/oauth", response_class=HTMLResponse)
async def google_oauth_admin_page(request: Request, admin: dict = Depends(require_admin_auth_cookie)):
    """Google OAuth administration interface"""
    add_log("INFO", "admin_google_oauth_page_access", f"Admin {admin.get('email')} accessed Google OAuth admin page")
    
    return templates.TemplateResponse("google_oauth_admin.html", {
        "request": request,
        "current_page": "google_oauth_admin",
        "admin": admin,
        "user_info": admin,
        "user_authenticated": True,
        "user_email": admin.get("email", ""),
        "cache_bust": int(time.time())
    })


@app.get("/admin/google/oauth/status")
async def google_oauth_status(request: Request, admin: dict = Depends(require_admin_auth_cookie)):
    """Get Google OAuth configuration and connection status"""
    admin_email = admin.get("email")
    
    try:
        add_log("INFO", "admin_google_oauth_status", f"Admin {admin_email} checking Google OAuth status")
        
        # Check if Google OAuth is configured in database
        ttw_manager = TTWOAuthManager()
        google_configured = await ttw_manager.is_google_oauth_app_configured()
        
        config = None
        if google_configured:
            config = await ttw_manager.get_google_oauth_app_config()
        
        # Check current session for Google auth
        google_connected = "user" in request.session if hasattr(request, 'session') else False
        
        return JSONResponse({
            "configured": google_configured,
            "connected": google_connected,
            "app_name": config.get("app_name", "") if config else "",
            "client_id": config.get("client_id", "") if config else "",
            "client_secret": config.get("client_secret", "") if config else "",
            "redirect_uri": config.get("redirect_uri", "") if config else "",
            "account_email": request.session.get("user", {}).get("email") if google_connected else None,
            "last_sync": request.session.get("user", {}).get("login_time") if google_connected else None,
            "token_expiry": request.session.get("user", {}).get("expires_at") if google_connected else None
        })
        
    except Exception as e:
        logger.error(f"Error getting Google OAuth status: {str(e)}")
        return JSONResponse({
            "status": "error",
            "error": str(e)
        }, status_code=500)


@app.post("/admin/google/oauth/config")
async def save_google_oauth_config(
    request: Request,
    config: dict,
    admin: dict = Depends(require_admin_auth_cookie)
):
    """Save Google OAuth configuration to database"""
    admin_email = admin.get("email")
    
    try:
        add_log("INFO", "admin_google_oauth_config_update", f"Admin {admin_email} updating Google OAuth configuration")
        
        # Validate required fields
        required_fields = ["client_id", "client_secret", "redirect_uri"]
        for field in required_fields:
            if not config.get(field):
                return JSONResponse({
                    "status": "error",
                    "detail": f"Missing required field: {field}"
                }, status_code=400)
        
        # Save configuration to database
        ttw_manager = TTWOAuthManager()
        result = await ttw_manager.configure_google_oauth_app(admin_email, config)
        
        if result:
            add_log("INFO", "admin_google_oauth_config_saved", f"Google OAuth config saved by {admin_email}")
            return JSONResponse({
                "status": "success",
                "message": "Google OAuth configuration saved successfully"
            })
        else:
            return JSONResponse({
                "status": "error",
                "detail": "Failed to save Google OAuth configuration"
            }, status_code=500)
        
    except Exception as e:
        logger.error(f"Error saving Google OAuth config: {str(e)}")
        add_log("ERROR", "admin_google_oauth_config_error", f"Error saving Google OAuth config by {admin_email}: {str(e)}")
        return JSONResponse({
            "status": "error",
            "error": str(e)
        }, status_code=500)


@app.delete("/admin/google/oauth/config")
async def clear_google_oauth_config(admin: dict = Depends(require_admin_auth_cookie)):
    """Clear Google OAuth configuration"""
    admin_email = admin.get("email")
    
    try:
        add_log("INFO", "admin_google_oauth_config_clear", f"Admin {admin_email} clearing Google OAuth configuration")
        
        ttw_manager = TTWOAuthManager()
        result = await ttw_manager.remove_google_oauth_app(admin_email)
        
        if result:
            add_log("INFO", "admin_google_oauth_config_cleared", f"Google OAuth config cleared by {admin_email}")
            return JSONResponse({
                "status": "success",
                "message": "Google OAuth configuration cleared successfully"
            })
        else:
            return JSONResponse({
                "status": "error",
                "detail": "Failed to clear Google OAuth configuration"
            }, status_code=500)
        
    except Exception as e:
        logger.error(f"Error clearing Google OAuth config: {str(e)}")
        add_log("ERROR", "admin_google_oauth_config_clear_error", f"Error clearing Google OAuth config by {admin_email}: {str(e)}")
        return JSONResponse({
            "status": "error",
            "error": str(e)
        }, status_code=500)


@app.get("/admin/google/oauth/authorize")
async def initiate_google_oauth(request: Request, admin: dict = Depends(require_admin_auth_session)):
    """Initiate Google OAuth authorization flow"""
    admin_email = admin.get("email")
    
    try:
        add_log("INFO", "admin_google_oauth_initiate", f"Admin {admin_email} initiating Google OAuth authorization")
        
        # Get redirect URI from environment
        redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/callback")
        
        # Generate a new state parameter for CSRF protection
        import secrets
        state = secrets.token_urlsafe(32)
        request.session['oauth_state'] = state
        
        # Use existing OAuth flow with proper async/await
        auth_result = await oauth.google.authorize_redirect(
            request, 
            redirect_uri,
            state=state
        )
        
        # Extract the redirect URL from the response
        if hasattr(auth_result, 'headers') and 'location' in auth_result.headers:
            auth_url = auth_result.headers['location']
        else:
            # Fallback - construct URL manually
            auth_url = str(auth_result)
        
        return JSONResponse({
            "auth_url": auth_url
        })
        
    except Exception as e:
        logger.error(f"Error initiating Google OAuth: {str(e)}")
        add_log("ERROR", "admin_google_oauth_initiate_error", f"Error initiating Google OAuth for {admin_email}: {str(e)}")
        return JSONResponse({
            "status": "error",
            "detail": str(e)
        }, status_code=500)


@app.post("/admin/google/oauth/revoke")
async def revoke_google_oauth(request: Request, admin: dict = Depends(require_admin_auth_cookie)):
    """Revoke Google OAuth access"""
    admin_email = admin.get("email")
    
    try:
        add_log("INFO", "admin_google_oauth_revoke", f"Admin {admin_email} revoking Google OAuth access")
        
        # Clear session
        if hasattr(request, 'session'):
            request.session.clear()
        
        add_log("INFO", "admin_google_oauth_revoked", f"Google OAuth access revoked for {admin_email}")
        
        return JSONResponse({
            "status": "success",
            "message": "Google OAuth access revoked successfully"
        })
        
    except Exception as e:
        logger.error(f"Error revoking Google OAuth: {str(e)}")
        add_log("ERROR", "admin_google_oauth_revoke_error", f"Error revoking Google OAuth for {admin_email}: {str(e)}")
        return JSONResponse({
            "status": "error",
            "error": str(e)
        }, status_code=500)


@app.get("/admin/google/oauth/test")
async def test_google_oauth_connection(admin: dict = Depends(require_admin_auth_session)):
    """Test Google OAuth connection"""
    admin_email = admin.get("email")
    
    try:
        add_log("INFO", "admin_google_oauth_test", f"Admin {admin_email} testing Google OAuth connection")
        
        google_configured = bool(os.getenv("GOOGLE_CLIENT_ID") and os.getenv("GOOGLE_CLIENT_SECRET"))
        
        if not google_configured:
            return JSONResponse({
                "status": "error",
                "detail": "Google OAuth not configured"
            }, status_code=400)
        
        # Test configuration validity
        add_log("INFO", "admin_google_oauth_test_success", f"Google OAuth test successful for {admin_email}")
        
        return JSONResponse({
            "status": "success",
            "message": "Google OAuth configuration is valid"
        })
        
    except Exception as e:
        logger.error(f"Error testing Google OAuth: {str(e)}")
        add_log("ERROR", "admin_google_oauth_test_error", f"Error testing Google OAuth for {admin_email}: {str(e)}")
        return JSONResponse({
            "status": "error",
            "error": str(e)
        }, status_code=500)


@app.get("/admin/google/oauth/profile")
async def get_google_profile(request: Request, admin: dict = Depends(require_admin_auth_session)):
    """Retrieve Google profile information using current session token"""
    import httpx
    admin_email = admin.get("email")
    
    try:
        add_log("INFO", "admin_google_profile_request", f"Admin {admin_email} requesting Google profile data")
        
        # Check if user has an active Google session
        if not hasattr(request, 'session') or 'user' not in request.session:
            add_log("WARNING", "admin_google_profile_no_session", f"Admin {admin_email} has no active Google session")
            return JSONResponse({
                "status": "error",
                "message": "No active Google session. Please authorize Google access first."
            }, status_code=401)
        
        user_session = request.session.get('user', {})
        access_token = user_session.get('access_token')
        
        if not access_token:
            add_log("WARNING", "admin_google_profile_no_token", f"Admin {admin_email} session missing access token")
            return JSONResponse({
                "status": "error", 
                "message": "No Google access token found. Please re-authorize Google access."
            }, status_code=401)
        
        # Log the token retrieval (without exposing the actual token)
        add_log("DEBUG", "admin_google_profile_token_found", 
               f"Admin {admin_email} - Google access token found, length: {len(access_token) if access_token else 0}")
        
        # Make request to Google People API for profile information
        profile_url = "https://www.googleapis.com/oauth2/v2/userinfo"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json"
        }
        
        add_log("DEBUG", "admin_google_profile_api_request", 
               f"Admin {admin_email} - Making request to Google People API")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(profile_url, headers=headers)
            
            # Log the API response details
            add_log("DEBUG", "admin_google_profile_api_response", 
                   f"Admin {admin_email} - Google API response status: {response.status_code}")
            
            if response.status_code == 200:
                profile_data = response.json()
                
                # Log successful profile retrieval (without sensitive data)
                add_log("INFO", "admin_google_profile_success", 
                       f"Admin {admin_email} - Successfully retrieved Google profile for user: {profile_data.get('email', 'unknown')}")
                
                # Extract interesting data for debugging
                debug_info = {
                    "api_endpoint": profile_url,
                    "response_time": response.elapsed.total_seconds() if hasattr(response, 'elapsed') else "N/A",
                    "user_verified_email": profile_data.get('verified_email', False),
                    "user_locale": profile_data.get('locale', 'unknown'),
                    "profile_picture_available": bool(profile_data.get('picture')),
                    "google_user_id": profile_data.get('id', 'unknown')
                }
                
                add_log("DEBUG", "admin_google_profile_debug_info", 
                       f"Admin {admin_email} - Google profile debug data: {debug_info}")
                
                return JSONResponse({
                    "status": "success",
                    "profile": profile_data,
                    "debug_info": debug_info,
                    "session_info": {
                        "token_length": len(access_token),
                        "session_user_email": user_session.get('email'),
                        "session_expires_at": user_session.get('expires_at')
                    }
                })
            
            elif response.status_code == 401:
                add_log("WARNING", "admin_google_profile_token_expired", 
                       f"Admin {admin_email} - Google access token expired or invalid")
                return JSONResponse({
                    "status": "error",
                    "message": "Google access token expired or invalid. Please re-authorize Google access.",
                    "error_code": "TOKEN_EXPIRED"
                }, status_code=401)
            
            else:
                error_text = response.text
                add_log("ERROR", "admin_google_profile_api_error", 
                       f"Admin {admin_email} - Google API error: {response.status_code} - {error_text}")
                return JSONResponse({
                    "status": "error",
                    "message": f"Google API error: {response.status_code}",
                    "details": error_text
                }, status_code=response.status_code)
                
    except httpx.RequestError as e:
        add_log("ERROR", "admin_google_profile_network_error", 
               f"Admin {admin_email} - Network error contacting Google API: {str(e)}")
        return JSONResponse({
            "status": "error",
            "message": "Network error contacting Google API",
            "details": str(e)
        }, status_code=500)
        
    except Exception as e:
        logger.error(f"Error retrieving Google profile: {str(e)}")
        add_log("ERROR", "admin_google_profile_error", 
               f"Admin {admin_email} - Error retrieving Google profile: {str(e)}")
        return JSONResponse({
            "status": "error",
            "message": f"Error retrieving Google profile: {str(e)}"
        }, status_code=500)


# --- LinkedIn OAuth Admin Routes ---

@app.get("/admin/linkedin/oauth", response_class=HTMLResponse)
async def linkedin_oauth_admin_page(request: Request, admin: dict = Depends(require_admin_auth_cookie)):
    """LinkedIn OAuth administration interface"""
    add_log("INFO", "admin_linkedin_oauth_page_access", f"Admin {admin.get('email')} accessed LinkedIn OAuth admin page")
    
    return templates.TemplateResponse("linkedin_oauth_admin.html", {
        "request": request,
        "current_page": "linkedin_oauth_admin",
        "admin": admin,
        "user_info": admin,
        "user_authenticated": True,
        "user_email": admin.get("email", "")
    })


@app.get("/admin/linkedin/oauth/status")
async def linkedin_oauth_status(request: Request, admin: dict = Depends(require_admin_auth_cookie)):
    """Get LinkedIn OAuth configuration and connection status"""
    admin_email = admin.get("email")
    
    try:
        add_log("INFO", "admin_linkedin_oauth_status", f"Admin {admin_email} checking LinkedIn OAuth status")
        
        # Check if LinkedIn OAuth is configured in database
        ttw_manager = TTWOAuthManager()
        linkedin_configured = await ttw_manager.is_linkedin_oauth_app_configured()
        
        config = None
        if linkedin_configured:
            config = await ttw_manager.get_linkedin_oauth_app_config()
        
        # Check current session for LinkedIn auth
        linkedin_connected = "linkedin_user" in request.session if hasattr(request, 'session') else False
        
        return JSONResponse({
            "configured": linkedin_configured,
            "connected": linkedin_connected,
            "app_name": config.get("app_name", "") if config else "",
            "client_id": config.get("client_id", "") if config else "",
            "client_secret": config.get("client_secret", "") if config else "",
            "redirect_uri": config.get("redirect_uri", "") if config else "",
            "account_email": request.session.get("linkedin_user", {}).get("email") if linkedin_connected else None,
            "last_sync": request.session.get("linkedin_user", {}).get("login_time") if linkedin_connected else None,
            "token_expiry": request.session.get("linkedin_user", {}).get("expires_at") if linkedin_connected else None
        })
        
    except Exception as e:
        logger.error(f"Error getting LinkedIn OAuth status: {str(e)}")
        return JSONResponse({
            "status": "error",
            "error": str(e)
        }, status_code=500)


@app.get("/admin/linkedin/config")
async def get_linkedin_oauth_config_for_form(admin: dict = Depends(require_admin_auth_cookie)):
    """Get LinkedIn OAuth configuration for admin form"""
    admin_email = admin.get("email")
    
    try:
        add_log("INFO", "admin_linkedin_config_form_load", f"Admin {admin_email} loading LinkedIn OAuth config form")
        
        # Get current LinkedIn OAuth config from oauth_apps table (consistent with status route)
        query = """
            SELECT app_name, client_id, redirect_uri, scopes, is_active, created_by, created_at
            FROM oauth_apps 
            WHERE provider = 'linkedin' AND is_active = true
            ORDER BY created_at DESC
            LIMIT 1
        """
        result = await database.fetch_one(query)
        
        if result:
            return JSONResponse({
                "app_name": result["app_name"] or "",
                "client_id": result["client_id"] or "",
                "client_secret": "",  # Never return the actual secret for security
                "redirect_uri": result["redirect_uri"] or "",
                "scopes": result["scopes"] or "r_liteprofile,r_emailaddress",
                "configured": True
            })
        else:
            return JSONResponse({
                "app_name": "blackburnsystems profile site",
                "client_id": "",
                "client_secret": "",
                "redirect_uri": "https://www.blackburnsystems.com/admin/linkedin/callback",
                "scopes": "r_liteprofile,r_emailaddress",
                "configured": False
            })
        
    except Exception as e:
        logger.error(f"Error getting LinkedIn OAuth config for form: {str(e)}")
        return JSONResponse({
            "status": "error",
            "error": str(e)
        }, status_code=500)


@app.post("/admin/linkedin/config")
async def save_linkedin_config_shortcut(
    config: dict,
    admin: dict = Depends(require_admin_auth_cookie)
):
    """Save LinkedIn OAuth configuration (shortcut route for JavaScript)"""
    # Forward to the main OAuth config route
    return await save_linkedin_oauth_config(config, admin)


@app.post("/admin/linkedin/oauth/config")
async def save_linkedin_oauth_config(
    request: Request,
    config: dict,
    admin: dict = Depends(require_admin_auth_cookie)
):
    """Save LinkedIn OAuth configuration to database"""
    admin_email = admin.get("email")
    
    try:
        add_log("INFO", "admin_linkedin_oauth_config_update", f"Admin {admin_email} updating LinkedIn OAuth configuration")
        
        # Validate required fields
        required_fields = ["client_id", "client_secret", "redirect_uri"]
        for field in required_fields:
            if not config.get(field):
                return JSONResponse({
                    "status": "error",
                    "detail": f"Missing required field: {field}"
                }, status_code=400)
        
        # Save configuration to database
        ttw_manager = TTWOAuthManager()
        result = await ttw_manager.configure_linkedin_oauth_app(admin_email, config)
        
        if result:
            add_log("INFO", "admin_linkedin_oauth_config_saved", f"LinkedIn OAuth config saved by {admin_email}")
            return JSONResponse({
                "status": "success",
                "message": "LinkedIn OAuth configuration saved successfully"
            })
        else:
            return JSONResponse({
                "status": "error",
                "detail": "Failed to save LinkedIn OAuth configuration"
            }, status_code=500)
        
    except Exception as e:
        logger.error(f"Error saving LinkedIn OAuth config: {str(e)}")
        add_log("ERROR", "admin_linkedin_oauth_config_save_error", f"Error saving LinkedIn OAuth config by {admin_email}: {str(e)}")
        return JSONResponse({
            "status": "error",
            "error": str(e)
        }, status_code=500)


@app.get("/admin/linkedin/test-config")
async def test_linkedin_config_shortcut(admin: dict = Depends(require_admin_auth_cookie)):
    """Test LinkedIn OAuth configuration (shortcut route for JavaScript)"""
    # Forward to the main OAuth test route
    return await test_linkedin_oauth_config(admin)


@app.delete("/admin/linkedin/oauth/config")
async def clear_linkedin_oauth_config(admin: dict = Depends(require_admin_auth_cookie)):
    """Clear LinkedIn OAuth configuration"""
    admin_email = admin.get("email")
    
    try:
        add_log("INFO", "admin_linkedin_oauth_config_clear", f"Admin {admin_email} clearing LinkedIn OAuth configuration")
        
        ttw_manager = TTWOAuthManager()
        result = await ttw_manager.remove_linkedin_oauth_app(admin_email)
        
        if result:
            add_log("INFO", "admin_linkedin_oauth_config_cleared", f"LinkedIn OAuth config cleared by {admin_email}")
            return JSONResponse({
                "status": "success",
                "message": "LinkedIn OAuth configuration cleared successfully"
            })
        else:
            return JSONResponse({
                "status": "error",
                "detail": "Failed to clear LinkedIn OAuth configuration"
            }, status_code=500)
        
    except Exception as e:
        logger.error(f"Error clearing LinkedIn OAuth config: {str(e)}")
        add_log("ERROR", "admin_linkedin_oauth_config_clear_error", f"Error clearing LinkedIn OAuth config by {admin_email}: {str(e)}")
        return JSONResponse({
            "status": "error",
            "error": str(e)
        }, status_code=500)


@app.get("/admin/linkedin/oauth/authorize")
async def initiate_linkedin_oauth(admin: dict = Depends(require_admin_auth_cookie)):
    """Initiate LinkedIn OAuth authorization flow"""
    admin_email = admin.get("email")
    
    try:
        add_log("INFO", "admin_linkedin_oauth_initiate", f"Admin {admin_email} initiating LinkedIn OAuth authorization")
        
        ttw_manager = TTWOAuthManager()
        auth_url, state = await ttw_manager.get_linkedin_authorization_url(admin_email)
        
        if auth_url:
            add_log("INFO", "admin_linkedin_oauth_url_generated", f"LinkedIn OAuth URL generated for {admin_email}")
            return JSONResponse({
                "auth_url": auth_url
            })
        else:
            return JSONResponse({
                "status": "error",
                "detail": "Failed to generate LinkedIn authorization URL. Check configuration."
            }, status_code=400)
        
    except Exception as e:
        logger.error(f"Error initiating LinkedIn OAuth: {str(e)}")
        add_log("ERROR", "admin_linkedin_oauth_initiate_error", f"Error initiating LinkedIn OAuth for {admin_email}: {str(e)}")
        return JSONResponse({
            "status": "error",
            "error": str(e)
        }, status_code=500)


@app.post("/admin/linkedin/oauth/revoke")
async def revoke_linkedin_oauth(admin: dict = Depends(require_admin_auth_cookie)):
    """Revoke LinkedIn OAuth access"""
    admin_email = admin.get("email")
    
    try:
        add_log("INFO", "admin_linkedin_oauth_revoke", f"Admin {admin_email} revoking LinkedIn OAuth access")
        
        ttw_manager = TTWOAuthManager()
        result = await ttw_manager.remove_linkedin_connection(admin_email)
        
        if result:
            add_log("INFO", "admin_linkedin_oauth_revoked", f"LinkedIn OAuth access revoked for {admin_email}")
            return JSONResponse({
                "status": "success",
                "message": "LinkedIn OAuth access revoked successfully"
            })
        else:
            return JSONResponse({
                "status": "error",
                "detail": "Failed to revoke LinkedIn OAuth access"
            }, status_code=500)
        
    except Exception as e:
        logger.error(f"Error revoking LinkedIn OAuth: {str(e)}")
        add_log("ERROR", "admin_linkedin_oauth_revoke_error", f"Error revoking LinkedIn OAuth for {admin_email}: {str(e)}")
        return JSONResponse({
            "status": "error",
            "error": str(e)
        }, status_code=500)


@app.get("/admin/linkedin/oauth/test")
async def test_linkedin_oauth_config(admin: dict = Depends(require_admin_auth_cookie)):
    """Test LinkedIn OAuth configuration"""
    admin_email = admin.get("email")
    
    try:
        add_log("INFO", "admin_linkedin_oauth_config_test", f"Admin {admin_email} testing LinkedIn OAuth configuration")
        
        ttw_manager = TTWOAuthManager()
        
        # Check if OAuth app is configured
        is_configured = await ttw_manager.is_oauth_app_configured()
        
        if is_configured:
            config = await ttw_manager.get_oauth_app_config()
            if config:
                add_log("INFO", "admin_linkedin_oauth_config_test_success", f"LinkedIn OAuth config test successful for {admin_email}")
                return JSONResponse({
                    "status": "success",
                    "message": f"LinkedIn OAuth configuration is valid. App: {config.get('app_name', 'Unknown')}"
                })
            else:
                add_log("ERROR", "admin_linkedin_oauth_config_test_failure", f"LinkedIn OAuth config test failed for {admin_email}: Config not found")
                return JSONResponse({
                    "status": "error",
                    "detail": "LinkedIn OAuth configuration not found in database"
                }, status_code=400)
        else:
            add_log("ERROR", "admin_linkedin_oauth_config_test_failure", f"LinkedIn OAuth config test failed for {admin_email}: Not configured")
            return JSONResponse({
                "status": "error",
                "detail": "LinkedIn OAuth application is not configured"
            }, status_code=400)
        
    except Exception as e:
        logger.error(f"Error testing LinkedIn OAuth config: {str(e)}")
        add_log("ERROR", "admin_linkedin_oauth_config_test_error", f"Error testing LinkedIn OAuth config for {admin_email}: {str(e)}")
        return JSONResponse({
            "status": "error",
            "error": str(e)
        }, status_code=500)


@app.get("/admin/linkedin/oauth/test-api")
async def test_linkedin_oauth_api(admin: dict = Depends(require_admin_auth_cookie)):
    """Test LinkedIn OAuth API access"""
    admin_email = admin.get("email")
    
    try:
        add_log("INFO", "admin_linkedin_oauth_api_test", f"Admin {admin_email} testing LinkedIn OAuth API access")
        
        sync_service = TTWLinkedInSync(admin_email)
        
        # Test API access by getting profile info
        profile_data = await sync_service.get_linkedin_profile()
        
        if profile_data:
            add_log("INFO", "admin_linkedin_oauth_api_test_success", f"LinkedIn OAuth API test successful for {admin_email}")
            return JSONResponse({
                "status": "success",
                "message": "LinkedIn API access test successful",
                "profile_name": profile_data.get("localizedFirstName", "") + " " + profile_data.get("localizedLastName", "")
            })
        else:
            add_log("ERROR", "admin_linkedin_oauth_api_test_failure", f"LinkedIn OAuth API test failed for {admin_email} - no profile data")
            return JSONResponse({
                "status": "error",
                "detail": "Failed to retrieve LinkedIn profile data. Check token validity."
            }, status_code=400)
        
    except Exception as e:
        logger.error(f"Error testing LinkedIn OAuth API: {str(e)}")
        add_log("ERROR", "admin_linkedin_oauth_api_test_error", f"Error testing LinkedIn OAuth API for {admin_email}: {str(e)}")
        return JSONResponse({
            "status": "error",
            "error": str(e)
        }, status_code=500)


@app.post("/admin/linkedin/sync")
async def sync_linkedin_profile_data(admin: dict = Depends(require_admin_auth_cookie)):
    """Sync LinkedIn profile data to portfolio database"""
    admin_email = admin.get("email")
    
    try:
        add_log("INFO", "admin_linkedin_sync_initiate", f"Admin {admin_email} initiating LinkedIn profile data sync")
        
        sync_service = TTWLinkedInSync(admin_email)
        result = await sync_service.sync_profile_data()
        
        if result.get("success"):
            add_log("INFO", "admin_linkedin_sync_success", f"LinkedIn profile sync successful for {admin_email}: {result.get('message')}")
            return JSONResponse({
                "status": "success",
                "message": result.get("message", "LinkedIn profile data synced successfully"),
                "synced_data": result.get("synced_data", {})
            })
        else:
            add_log("ERROR", "admin_linkedin_sync_failure", f"LinkedIn profile sync failed for {admin_email}: {result.get('error')}")
            return JSONResponse({
                "status": "error",
                "detail": result.get("error", "LinkedIn profile sync failed")
            }, status_code=400)
        
    except Exception as e:
        logger.error(f"Error syncing LinkedIn profile: {str(e)}")
        add_log("ERROR", "admin_linkedin_sync_error", f"Error syncing LinkedIn profile for {admin_email}: {str(e)}")
        return JSONResponse({
            "status": "error",
            "error": str(e)
        }, status_code=500)


# --- OAuth Callback Routes (renamed for clarity) ---

@app.get("/admin/linkedin/oauth/callback")
async def linkedin_oauth_callback(request: Request, code: str = None, state: str = None, error: str = None):
    """Handle LinkedIn OAuth callback"""
    
    try:
        if error:
            add_log("ERROR", "linkedin_oauth_callback_error", f"LinkedIn OAuth callback error: {error}")
            return templates.TemplateResponse("linkedin_oauth_error.html", {
                "request": request,
                "error": error
            })
        
        if not code:
            add_log("linkedin_oauth_callback_no_code", "LinkedIn OAuth callback missing authorization code")
            return templates.TemplateResponse("linkedin_oauth_error.html", {
                "request": request,
                "error": "Missing authorization code"
            })
        
        # Extract admin email from state if available
        admin_email = None
        if state:
            try:
                import json
                state_data = json.loads(state)
                admin_email = state_data.get("admin_email")
            except:
                pass
        
        if not admin_email:
            add_log("linkedin_oauth_callback_no_admin", "LinkedIn OAuth callback missing admin email in state")
            return templates.TemplateResponse("linkedin_oauth_error.html", {
                "request": request,
                "error": "Invalid state parameter"
            })
        
        add_log("INFO", "linkedin_oauth_callback_processing", f"Processing LinkedIn OAuth callback for admin {admin_email}")
        
        # Use TTW OAuth Manager to handle the callback
        ttw_manager = TTWOAuthManager()
        try:
            # Verify the state parameter
            state_data = ttw_manager.verify_linkedin_state(state)
            
            # Exchange code for tokens
            token_result = await ttw_manager.exchange_linkedin_code_for_tokens(code, state_data)
            
            add_log("INFO", "linkedin_oauth_callback_success", f"LinkedIn OAuth callback successful for admin {admin_email}")
            return templates.TemplateResponse("linkedin_oauth_success.html", {
                "request": request,
                "message": "LinkedIn OAuth authorization successful!"
            })
        except Exception as oauth_error:
            logger.error(f"OAuth exchange failed: {str(oauth_error)}")
            add_log("ERROR", "linkedin_oauth_callback_failure", f"LinkedIn OAuth callback failed for admin {admin_email}: {str(oauth_error)}")
            return templates.TemplateResponse("linkedin_oauth_error.html", {
                "request": request,
                "error": f"OAuth exchange failed: {str(oauth_error)}"
            })
        
    except Exception as e:
        logger.error(f"Error in LinkedIn OAuth callback: {str(e)}")
        add_log("INFO", "linkedin_oauth_callback_exception", f"Exception in LinkedIn OAuth callback: {str(e)}")
        return templates.TemplateResponse("linkedin_oauth_error.html", {
            "request": request,
            "error": f"Callback processing error: {str(e)}"
        })


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
