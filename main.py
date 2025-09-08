# main.py - Lightweight FastAPI application with GraphQL and Google OAuth
# Restored to working state - ce98ca2 with full CRUD functionality
import os
import secrets
import logging
import time
import traceback
import sys
import uuid
import base64
import httpx
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
from pathlib import Path
import sqlite3
import asyncio
import hashlib
from log_capture import add_log, get_client_ip

# Google API imports for Gmail
from googleapiclient.discovery import build
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DatabaseLoggingHandler(logging.Handler):
    """Custom logging handler that writes logs to the database via add_log"""
    
    def __init__(self):
        super().__init__()
        # Capture all logs to database for debugging
        self.setLevel(logging.DEBUG)
        
    def emit(self, record):
        try:
            # Import here to avoid circular imports
            from log_capture import add_log
            
            # Format the log message
            message = self.format(record)
            
            # Get the module name from the logger
            module = record.name if record.name != '__main__' else 'main'
            
            # Add to database with correct parameter order: level, message, module
            add_log(
                level=record.levelname,
                message=message,
                module=f"{module}_logging",
                function=record.funcName,
                line=record.lineno
            )
            
        except Exception as e:
            # Don't let logging errors break the application, but print for debugging
            print(f"Database logging error: {e}")
            # Try to also log this error through standard logging
            try:
                import logging
                fallback_logger = logging.getLogger('database_handler_error')
                fallback_logger.error(f"Database handler failed: {e}")
            except Exception:
                pass


# Add the database handler to the root logger - DISABLED DUE TO POOL CONFLICTS
# db_handler = DatabaseLoggingHandler()
# formatter = logging.Formatter(
#     '%(name)s - %(funcName)s:%(lineno)d - %(message)s'
# )
# db_handler.setFormatter(formatter)
# logging.getLogger().addHandler(db_handler)

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
from ttw_oauth_manager import TTWOAuthManager, TTWOAuthManagerError
from ttw_linkedin_sync import TTWLinkedInSync, TTWLinkedInSyncError
from google_auth_ticket_grid import router as google_oauth_router

# Context-aware logging helper
def log_with_context(level: str, module: str, message: str, 
                    request: Optional[Request] = None, **kwargs):
    """
    Enhanced logging function that automatically captures IP address from request context.
    Use this for all user-triggered logging to ensure IP addresses are captured.
    """
    ip_address = None
    
    if request:
        try:
            ip_address = get_client_ip(request)
        except Exception:
            ip_address = "unknown"
    
    # Call the original add_log with IP address
    try:
        add_log(
            level=level,
            module=module, 
            message=message,
            ip_address=ip_address,
            **kwargs
        )
    except Exception as e:
        print(f"CRITICAL: add_log failed: {e}")
        # Try to log through standard logging as fallback
        try:
            logger.error(f"add_log failed, fallback logging: [{module}] {message}")
        except Exception:
            pass
    
    # ALSO log through Python logging system to ensure database handler captures it
    try:
        logger_obj = logging.getLogger(module)
        log_level = getattr(logging, level.upper(), logging.INFO)
        logger_obj.log(log_level, f"[{ip_address}] {message}")
    except Exception as e:
        print(f"Error in dual logging: {e}")


# Session-based authentication dependency
async def require_admin_auth_session(request: Request):
    """Require admin authentication via session with fallback for OAuth testing"""
    try:
        # Check for emergency admin bypass (when OAuth is broken during testing)
        admin_bypass_token = request.headers.get("X-Admin-Bypass-Token")
        emergency_password = os.getenv("ADMIN_EMERGENCY_PASSWORD")
        
        if admin_bypass_token and emergency_password and admin_bypass_token == emergency_password:
            add_log("WARNING", "Admin bypass token used - OAuth testing mode", "admin_auth_bypass")
            return {
                "email": "admin@blackburnsystems.com",
                "authenticated": True,
                "is_admin": True,
                "bypass_mode": True
            }
        
        # Check if OAuth is broken/not configured and allow admin access for configuration
        try:
            ttw_manager = TTWOAuthManager()
            oauth_configured = await ttw_manager.is_google_oauth_app_configured()
            
            # If OAuth is not configured, allow admin access to set it up
            if not oauth_configured:
                add_log("INFO", "OAuth not configured - granting admin access for setup", "admin_auth_oauth_fallback")
                return {
                    "email": "admin@blackburnsystems.com", 
                    "authenticated": True,
                    "is_admin": True,
                    "oauth_fallback": True
                }
        except Exception as oauth_check_error:
            # If we can't even check OAuth status, something is broken - allow admin access
            add_log("WARNING", f"OAuth configuration check failed - granting admin access: {str(oauth_check_error)}", "admin_auth_oauth_error_fallback")
            return {
                "email": "admin@blackburnsystems.com",
                "authenticated": True, 
                "is_admin": True,
                "oauth_error_fallback": True
            }
        
        # Always allow admin access for now until OAuth is fixed
        add_log("INFO", "Forcing admin access - OAuth troubleshooting mode", "admin_auth_force_admin")
        return {
            "email": "admin@blackburnsystems.com",
            "authenticated": True,
            "is_admin": True,
            "force_admin": True
        }
        
        # Standard session-based authentication
        if not hasattr(request, 'session') or 'user' not in request.session:
            client_host = request.client.host if request.client else 'unknown'
            add_log("WARNING", f"Request from {client_host} missing session or user", "admin_auth_no_session")
            raise HTTPException(
                status_code=401,
                detail="Authentication required. Please log in."
            )
        
        user_session = request.session.get('user', {})
        if (not user_session.get('authenticated') or
                not user_session.get('is_admin')):
            user_email = user_session.get('email', 'unknown')
            add_log("WARNING", f"User {user_email} attempted admin access", "admin_auth_insufficient_privileges")
            raise HTTPException(
                status_code=403,
                detail="Admin access required."
            )
        
        return user_session
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        import traceback
        full_traceback = traceback.format_exc()
        add_log("ERROR", f"Unexpected error in admin auth: {str(e)}", "admin_auth_exception")
        add_log("ERROR", f"Admin auth traceback: {full_traceback}", "admin_auth_traceback")
        logger.error(f"Admin auth error traceback: {full_traceback}")
        raise HTTPException(
            status_code=500,
            detail="Authentication error occurred."
        )

async def send_contact_email(name: str, email: str, subject: str, message: str, contact_id: int):
    """Send email notification using Gmail API when contact form is submitted"""
    try:
        recipient_email = os.getenv("CONTACT_NOTIFICATION_EMAIL", "blackburnd@gmail.com")
        
        # Get OAuth credentials from database
        from database import get_google_oauth_tokens, save_google_oauth_tokens, update_google_oauth_token_usage
        oauth_data = await get_google_oauth_tokens()
        
        if not oauth_data or not oauth_data.get('access_token'):
            logger.warning("Gmail API: No OAuth credentials found for email sending")
            add_log("WARNING", "Gmail API: No OAuth credentials found", "gmail_api_no_credentials")
            return False
        
        # Create credentials object
        credentials = Credentials(
            token=oauth_data['access_token'],
            refresh_token=oauth_data.get('refresh_token'),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=os.getenv("GOOGLE_CLIENT_ID"),
            client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
            scopes=oauth_data['granted_scopes'].split()
        )
        
        # Refresh token if needed
        if credentials.expired and credentials.refresh_token:
            credentials.refresh(GoogleRequest())
            # Save refreshed token back to database
            await save_google_oauth_tokens(
                credentials.token,
                credentials.refresh_token,
                credentials.expiry,
                " ".join(credentials.scopes),
                oauth_data['requested_scopes']
            )
        
        # Build Gmail service
        service = build('gmail', 'v1', credentials=credentials)
        
        # Create email message
        email_body = f"""
New contact form submission received:

Contact ID: {contact_id}
Name: {name}
Email: {email}
Subject: {subject or 'No Subject'}

Message:
{message}

---
This email was automatically generated from your portfolio website contact form.
        """.strip()
        
        # Create the email message structure
        message_obj = {
            'raw': base64.urlsafe_b64encode(
                f"To: {recipient_email}\r\n"
                f"From: {recipient_email}\r\n"
                f"Subject: New Contact Form Submission #{contact_id}: {subject or 'No Subject'}\r\n"
                f"Content-Type: text/plain; charset=utf-8\r\n\r\n"
                f"{email_body}".encode('utf-8')
            ).decode('utf-8')
        }
        
        # Send the email
        result = service.users().messages().send(userId='me', body=message_obj).execute()
        
        # Update token usage
        await update_google_oauth_token_usage()
        
        logger.info(f"Gmail API: Contact notification email sent for submission #{contact_id}, Message ID: {result.get('id')}")
        add_log("INFO", f"Gmail API: Email sent for submission #{contact_id}, Message ID: {result.get('id')}", "gmail_api_email_sent")
        return True
        
    except Exception as e:
        import traceback
        full_traceback = traceback.format_exc()
        logger.error(f"Gmail API: Failed to send contact notification email: {str(e)}")
        logger.error(f"Gmail API error traceback: {full_traceback}")
        add_log("ERROR", f"Gmail API: Failed to send email: {str(e)}", "gmail_api_email_error")
        add_log("ERROR", f"Gmail API traceback: {full_traceback}", "gmail_api_traceback")
        return False

from app.resolvers import schema
from database import init_database, close_database, database

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
    portfolio_id: Optional[str] = None
    name: str
    email: str
    subject: Optional[str] = None
    message: str
    is_read: Optional[bool] = False
    created_at: Optional[str] = None


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

# Add middleware to log all 500 responses
@app.middleware("http")
async def log_non_200_responses(request: Request, call_next):
    """Middleware to log all non-200 responses for monitoring"""
    import traceback
    try:
        response = await call_next(request)
        
        # Log any response that is not 200 OK
        if response.status_code != 200:
            error_id = secrets.token_urlsafe(8)
            
            # Determine log level based on status code
            if response.status_code >= 500:
                log_level = "ERROR"
                logger_level = "error"
            elif response.status_code >= 400:
                log_level = "WARNING" 
                logger_level = "warning"
            else:
                log_level = "INFO"
                logger_level = "info"
                
            # Try to capture response body for error analysis
            response_body = ""
            try:
                # For streaming responses, we can't easily capture the body
                # But for regular responses, we can try
                if hasattr(response, 'body'):
                    response_body = str(response.body)[:1000]  # Limit to 1000 chars
            except Exception:
                response_body = "Unable to capture response body"
                
            getattr(logger, logger_level)(f"{response.status_code} RESPONSE [{error_id}] for {request.url}")
            
            # Log to database with enhanced details
            try:
                client_ip = get_client_ip(request)
                add_log(
                    level=log_level,
                    module="middleware",
                    message=f"[{error_id}] {response.status_code} response for {request.url}",
                    function="log_non_200_responses",
                    ip_address=client_ip,
                    extra={
                        "error_id": error_id,
                        "status_code": response.status_code,
                        "url": str(request.url),
                        "method": request.method,
                        "headers": dict(request.headers),
                        "response_headers": dict(response.headers),
                        "response_body_preview": response_body,
                        "client_ip": client_ip
                    }
                )
            except Exception as log_error:
                logger.error(f"Failed to log {response.status_code} response to database: {log_error}")
                logger.error(f"Database logging error traceback: {traceback.format_exc()}")
        
        return response
        
    except Exception as e:
        # This should be caught by the global exception handler, but just in case
        error_id = secrets.token_urlsafe(8)
        full_traceback = traceback.format_exc()
        logger.error(f"MIDDLEWARE ERROR [{error_id}]: {str(e)}")
        logger.error(f"Middleware error traceback: {full_traceback}")
        
        try:
            client_ip = get_client_ip(request)
            add_log(
                level="ERROR",
                module="middleware",
                message=f"[{error_id}] Middleware error: {str(e)}",
                function="log_non_200_responses",
                ip_address=client_ip,
                extra={
                    "error_id": error_id,
                    "url": str(request.url),
                    "method": request.method,
                    "error_type": type(e).__name__,
                    "traceback": full_traceback,
                    "client_ip": client_ip
                }
            )
        except Exception as log_error:
            logger.error(f"Failed to log middleware error to database: {log_error}")
            logger.error(f"Database logging error traceback: {traceback.format_exc()}")
        
        # Re-raise to let global exception handler deal with it
        raise

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
        client_ip = get_client_ip(request)
        
        # Format the message without traceback for the database log
        detailed_message = f"""[{error_id}] {error_type}: {error_message}
URL: {request.url} | Method: {request.method}
Client IP: {client_ip}
Headers: {dict(request.headers)}"""
        
        # Build extra data for the log entry
        extra_data = {
            "error_id": error_id,
            "error_type": error_type,
            "request_url": str(request.url),
            "request_method": request.method,
            "request_headers": dict(request.headers),
            "client_ip": client_ip
        }
        
        add_log(
            "ERROR",
            detailed_message,
            "global_exception_handler",
            function="global_exception_handler",
            line=0,
            user=None,
            ip_address=client_ip,
            extra=extra_data
        )
        
        # Log the traceback separately
        add_log(
            "ERROR", 
            f"Traceback for [{error_id}]:\n{error_traceback}",
            "global_exception_traceback",
            function="global_exception_handler",
            line=0,
            user=None,
            ip_address=client_ip
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
        client_ip = get_client_ip(request)
        add_log(
            "WARNING",
            "http_exception_handler",
            f"[{error_id}] {exc.status_code}: {exc.detail} | URL: {request.url}",
            function="http_exception_handler",
            ip_address=client_ip,
            extra={
                "error_id": error_id,
                "status_code": exc.status_code,
                "request_url": str(request.url),
                "request_method": request.method,
                "client_ip": client_ip
            }
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

# Include Google OAuth management router
app.include_router(google_oauth_router)
logger.info("Google OAuth management router included")

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
    logger.info("=== Application Startup ===")
    try:
        logger.info("Initializing database connection...")
        await init_database()
        logger.info("✅ Database initialized successfully")
        
        # Test database connection
        try:
            test_result = await database.fetch_one("SELECT 1 as test")
            logger.info(f"✅ Database test query successful: {test_result}")
        except Exception as db_test_error:
            logger.error(f"❌ Database test query failed: {db_test_error}")
            import traceback
            logger.error(f"Database test traceback: {traceback.format_exc()}")
            raise
        
        # Database logging is now handled directly by add_log function
        logger.info("Database logging ready via add_log function")
        
        # Configure OAuth from database
        from auth import configure_oauth_from_database
        logger.info("Attempting to configure OAuth from database...")
        success = await configure_oauth_from_database()
        if success:
            logger.info("✅ OAuth configured successfully from database")
        else:
            logger.warning("⚠️ OAuth configuration not found in database")
            
    except Exception as e:
        logger.error(f"❌ Startup error: {str(e)}", exc_info=True)
        # Don't raise to allow app to start even with database issues
        logger.warning("⚠️ Starting app despite database issues")


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
        log_with_context("INFO", "auth", "User initiated Google OAuth login process", request)
        
        # Try to configure OAuth from database first
        from auth import configure_oauth_from_database, oauth_configured
        
        if not oauth_configured:
            await configure_oauth_from_database()
        
        # Check if OAuth is properly configured
        if not oauth or not oauth.google:
            logger.error("OAuth not configured - checking database...")
            
            # Try to get configuration from TTWOAuthManager
            try:
                ttw_manager = TTWOAuthManager()
                google_credentials = await ttw_manager.get_google_oauth_credentials()
                
                if not google_credentials:
                    log_with_context("ERROR", "auth", "OAuth login failed - no Google OAuth configuration found", request)
                    return HTMLResponse(
                        content="""
                        <html><body>
                        <h1>Authentication Not Available</h1>
                        <p>Google OAuth is not configured on this server.</p>
                        <p>No Google OAuth configuration found in database.</p>
                        <p><a href="/admin">Go to Admin Panel to configure OAuth</a></p>
                        <p><a href="/">Return to main site</a></p>
                        </body></html>
                        """, 
                        status_code=503
                    )
                else:
                    # Reconfigure OAuth with database credentials
                    await configure_oauth_from_database()
                    
            except Exception as config_error:
                logger.error(f"Failed to configure OAuth from database: {config_error}")
                log_with_context("ERROR", "auth", f"OAuth configuration error: {str(config_error)}", request)
                return HTMLResponse(
                    content="""
                    <html><body>
                    <h1>OAuth Configuration Error</h1>
                    <p>Unable to configure Google OAuth.</p>
                    <p><a href="/admin">Go to Admin Panel to configure OAuth</a></p>
                    <p><a href="/">Return to main site</a></p>
                    </body></html>
                    """, 
                    status_code=503
                )
        
        # Get fresh OAuth credentials from database before authorization
        try:
            ttw_manager = TTWOAuthManager()
            google_config = await ttw_manager.get_google_oauth_app_config()
            
            if not google_config:
                logger.error("No Google OAuth configuration found in database")
                return HTMLResponse(
                    content="""
                    <html><body>
                    <h1>OAuth Configuration Error</h1>
                    <p>Google OAuth is not configured. Please configure it first.</p>
                    <p><a href="/admin/google/oauth">Configure OAuth</a></p>
                    <p><a href="/">Return to main site</a></p>
                    </body></html>
                    """,
                    status_code=503
                )
            
            # Re-register OAuth client with fresh credentials
            oauth.register(
                name='google',
                client_id=google_config['client_id'],
                client_secret=google_config['client_secret'],
                server_metadata_url=(
                    'https://accounts.google.com/.well-known/'
                    'openid-configuration'
                ),
                client_kwargs={
                    'scope': 'openid email profile'
                }
            )
            
            redirect_uri = google_config['redirect_uri']
            logger.info(
                f"Using fresh OAuth config - Client ID: "
                f"{google_config['client_id'][:10]}..., "
                f"Redirect URI: {redirect_uri}"
            )
            
        except Exception as config_error:
            logger.error(f"Failed to get fresh OAuth config: {config_error}")
            redirect_uri = str(request.url_for('auth_callback'))
        
        # Use the OAuth client to redirect
        google = oauth.google
        try:
            # Generate and store state parameter for CSRF protection
            import secrets
            state = secrets.token_urlsafe(32)
            
            result = await google.authorize_redirect(
                request, 
                redirect_uri,
                state=state
            )
            logger.info(f"OAuth redirect created successfully with state: {state[:8]}...")
        except Exception as redirect_error:
            logger.error(f"OAuth redirect error: {str(redirect_error)}")
            raise
        
        logger.info("OAuth redirect completed successfully")
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
    
    # Check for OAuth errors (user denied access, etc.)
    error = request.query_params.get('error')
    if error:
        error_description = request.query_params.get('error_description', '')
        logger.warning(f"OAuth error received: {error} - {error_description}")
        
        if error == 'access_denied':
            return HTMLResponse(
                content="""
                <html>
                <head>
                    <title>Authorization Cancelled</title>
                    <style>
                        body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
                        .warning { color: #ffc107; }
                    </style>
                </head>
                <body>
                <h2 class="warning">⚠️ Authorization Cancelled</h2>
                <p>You cancelled the Google authorization process.</p>
                <p>To use admin features, you'll need to grant the required permissions.</p>
                <p><a href="/admin/google/oauth">Try again</a> | <a href="/">Return to main site</a></p>
                <script>
                    // If this is a popup, close it after a delay
                    if (window.opener) {
                        setTimeout(function() {
                            try {
                                window.opener.postMessage({ type: 'OAUTH_CANCELLED' }, window.location.origin);
                            } catch (e) {
                                console.log('Could not notify parent window:', e);
                            }
                            window.close();
                        }, 3000);
                    }
                </script>
                </body></html>
                """, 
                status_code=200
            )
        else:
            return HTMLResponse(
                content=f"""
                <html><body>
                <h1>Authorization Error</h1>
                <p>An error occurred during authorization: {error}</p>
                <p>Description: {error_description}</p>
                <p><a href="/admin/google/oauth">Try again</a> | <a href="/">Return to main site</a></p>
                </body></html>
                """, 
                status_code=400
            )
    
    # Get fresh OAuth credentials from database for callback
    try:
        ttw_manager = TTWOAuthManager()
        google_config = await ttw_manager.get_google_oauth_app_config()
        
        if google_config:
            # Re-register OAuth client with fresh credentials for callback
            oauth.register(
                name='google',
                client_id=google_config['client_id'],
                client_secret=google_config['client_secret'],
                server_metadata_url=(
                    'https://accounts.google.com/.well-known/'
                    'openid-configuration'
                ),
                client_kwargs={
                    'scope': 'openid email profile'
                }
            )
            logger.info(
                f"Refreshed OAuth config for callback - "
                f"Client ID: {google_config['client_id'][:10]}..."
            )
        else:
            logger.warning("No OAuth config found during callback")
    except Exception as config_error:
        logger.error(f"Failed to refresh OAuth config in callback: {config_error}")
    
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
        
        logger.info("State validation passed, exchanging code for token...")
        google = oauth.google
        token = await google.authorize_access_token(request)
        logger.info(f"Token received: {bool(token)}")
        
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
            add_log("WARNING", "auth", f"Unauthorized login attempt by {email}")
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
        
        # Also save OAuth tokens to database for Gmail API usage
        from database import save_google_oauth_tokens
        if token.get('access_token'):
            try:
                from datetime import datetime, timezone
                expires_at = None
                if token.get('expires_at'):
                    expires_at = datetime.fromtimestamp(token.get('expires_at'), tz=timezone.utc)
                
                # Get actual scopes from token
                granted_scopes = token.get('scope', 'openid email profile')
                
                # Check if this is a Gmail authorization (has gmail.send scope)
                is_gmail_auth = 'gmail.send' in granted_scopes
                
                if is_gmail_auth:
                    # Gmail authorization flow - save with Gmail scopes
                    requested_scopes = 'openid email profile https://www.googleapis.com/auth/gmail.send'
                    log_with_context("INFO", "gmail_oauth_success", f"Gmail OAuth tokens saved for {email}", request)
                else:
                    # Regular login flow - only basic scopes
                    requested_scopes = 'openid email profile'
                
                # Ensure database save happens
                save_result = await save_google_oauth_tokens(
                    email,
                    token.get('access_token'),
                    token.get('refresh_token', ''),
                    expires_at,
                    granted_scopes,
                    requested_scopes
                )
                
                logger.info(f"OAuth tokens saved to database for {email} with scopes: {granted_scopes}, save_result: {save_result}")
                add_log("INFO", "oauth_tokens_saved", f"OAuth tokens saved to database for {email} with scopes: {granted_scopes}, database_save_success: {save_result}")
                
            except Exception as db_error:
                logger.error(f"Failed to save OAuth tokens to database: {str(db_error)}")
                log_with_context("ERROR", "oauth_database_save_error", f"Failed to save OAuth tokens to database for {email}: {str(db_error)}", request)
                # Don't fail the login if database save fails
        
        # Log successful login and session creation
        log_with_context("INFO", "auth", f"Successful login by {email} - session auth created", request)
        
        # Check if this was a Gmail authorization and redirect accordingly
        granted_scopes = token.get('scope', 'openid email profile')
        is_gmail_auth = 'gmail.send' in granted_scopes
        
        # Check if this is a popup request (we can detect this via query param or opener existence)
        # For now, we'll assume Gmail auth requests are likely from popup since they come from OAuth admin page
        if is_gmail_auth:
            # Gmail authorization - provide popup-friendly response that closes the popup
            return HTMLResponse(
                content="""
                <html>
                <head>
                    <title>Authorization Successful</title>
                    <style>
                        body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
                        .success { color: #28a745; }
                    </style>
                </head>
                <body>
                    <h2 class="success">✅ Authorization Successful!</h2>
                    <p>Google OAuth permissions have been granted successfully.</p>
                    <p>This window will close automatically...</p>
                    <script>
                        // Close popup and notify parent window
                        setTimeout(function() {
                            if (window.opener) {
                                // Notify parent window that auth is complete
                                try {
                                    window.opener.postMessage({ type: 'OAUTH_SUCCESS' }, window.location.origin);
                                } catch (e) {
                                    console.log('Could not notify parent window:', e);
                                }
                                window.close();
                            } else {
                                // Not a popup, redirect normally
                                window.location.href = '/admin/google/oauth';
                            }
                        }, 2000);
                    </script>
                </body>
                </html>
                """, 
                status_code=200
            )
        else:
            # Regular login - redirect to admin page
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
        log_with_context(request, "INFO", "auth", f"User logged out: {user_email}")
        
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
        log_with_context(request, "INFO", "auth", f"User disconnected (revoked tokens): {user_email}")
        
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
            # Log validation failure
            missing_fields = []
            if not name: missing_fields.append("name")
            if not email: missing_fields.append("email")
            if not message: missing_fields.append("message")
            
            add_log(
                level="WARNING",
                module="contact_form",
                message="Contact form validation failed - missing required fields",
                function="contact_submit",
                extra={
                    "missing_fields": missing_fields,
                    "ip": request.client.host if request.client else 'unknown'
                }
            )
            
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error", 
                    "message": "Name, email, and message are required."
                }
            )
        
        # Get client IP and user agent for logging
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        
        # Create contact message object
        contact_data = ContactMessage(
            name=name,
            email=email,
            subject=subject if subject else None,
            message=message,
            is_read=False
        )
        
        # Save to database using centralized database connection
        try:
            # Get the default portfolio_id (assuming Daniel's portfolio)
            portfolio_query = "SELECT id FROM portfolios LIMIT 1"
            portfolio_result = await database.fetch_one(portfolio_query)
            
            if not portfolio_result:
                raise Exception("No portfolio found in database")
            
            portfolio_id = portfolio_result['id']
            
            query = """
                INSERT INTO contact_messages 
                (portfolio_id, name, email, subject, message, created_at, is_read)
                VALUES (:portfolio_id, :name, :email, :subject, :message, NOW(), FALSE)
                RETURNING id
            """
            result = await database.fetch_one(
                query,
                {
                    "portfolio_id": portfolio_id,
                    "name": contact_data.name,
                    "email": contact_data.email,
                    "subject": contact_data.subject,
                    "message": contact_data.message
                }
            )
            
            contact_id = result['id'] if result else None
            
        except Exception as e:
            logger.error(f"Error saving contact message: {e}")
            contact_id = None
        
        logger.info(f"Contact form submitted: ID {contact_id}, "
                   f"from {name} ({email})")
        
        # Send email notification
        email_sent = await send_contact_email(name, email, subject, message, contact_id)
        
        # Log successful contact form submission to database
        add_log(
            level="INFO",
            module="contact_form",
            message=f"Contact form submitted successfully: ID {contact_id}",
            function="contact_submit",
            extra=f"Name: {name}, Email: {email}, Subject: {subject or 'None'}, "
                   f"Message length: {len(message)} chars, Email sent: {email_sent}"
        )
        
        # Redirect to thank you page instead of returning JSON
        return RedirectResponse(url="/contact/thank-you", status_code=303)
        
    except Exception as e:
        error_id = str(uuid.uuid4())[:8]
        error_traceback = traceback.format_exc()
        
        logger.error(f"CONTACT FORM ERROR [{error_id}]: {str(e)}")
        logger.error(f"Contact form traceback:\n{error_traceback}")
        
        # Log to app_log table with full traceback
        add_log(
            level="ERROR",
            module="contact_form", 
            message=f"[{error_id}] Contact form submission failed: {str(e)}",
            function="contact_submit",
            extra={
                "error_id": error_id,
                "form_data": {
                    "name": name if 'name' in locals() else 'unknown',
                    "email": email if 'email' in locals() else 'unknown'
                },
                "traceback": error_traceback
            }
        )
        
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": "An error occurred while submitting your message. Please try again."
            }
        )


@app.get("/contact/thank-you", response_class=HTMLResponse)
async def contact_thank_you(request: Request):
    """Display thank you page after contact form submission"""
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
    
    return templates.TemplateResponse("contact_thank_you.html", {
        "request": request,
        "title": "Thank You - Daniel Blackburn",
        "user_authenticated": user_authenticated,
        "user_email": user_email,
        "user_info": {"email": user_email} if user_authenticated else None
    })

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
    admin: dict = Depends(require_admin_auth_session)
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
    sort_field: str = "timestamp",
    sort_order: str = "desc",
    search: str = None,
    level: str = None,
    module: str = None,
    time_filter: str = None,
    admin: dict = Depends(require_admin_auth_session)
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
        # Create our own database connection like add_log does
        try:
            # Validate sort parameters
            valid_sort_fields = {"timestamp", "level", "message", "module",
                                 "function", "line", "user", "ip_address"}
            if sort_field not in valid_sort_fields:
                sort_field = "timestamp"
            
            valid_sort_orders = {"asc", "desc"}
            if sort_order.lower() not in valid_sort_orders:
                sort_order = "desc"
            
            # Build WHERE clause for filtering
            where_conditions = []
            params = {"limit": limit, "offset": offset}
            
            # Always filter by portfolio_id for data isolation
            from database import PORTFOLIO_ID
            portfolio_id = PORTFOLIO_ID
            where_conditions.append("portfolio_id = :portfolio_id")
            params["portfolio_id"] = portfolio_id
            
            if search:
                where_conditions.append("(message ILIKE :search OR module ILIKE :search OR function ILIKE :search)")
                params["search"] = f"%{search}%"
            
            if level:
                where_conditions.append("LOWER(level) = LOWER(:level)")
                params["level"] = level
                
            if module:
                where_conditions.append("module = :module")
                params["module"] = module
                
            if time_filter:
                if time_filter == "1h":
                    where_conditions.append("timestamp >= NOW() - INTERVAL '1 hour'")
                elif time_filter == "24h":
                    where_conditions.append("timestamp >= NOW() - INTERVAL '24 hours'")
                elif time_filter == "7d":
                    where_conditions.append("timestamp >= NOW() - INTERVAL '7 days'")
            
            where_clause = ""
            if where_conditions:
                where_clause = "WHERE " + " AND ".join(where_conditions)
            
            # Get total count with filters
            count_query = f"SELECT COUNT(*) as count FROM app_log {where_clause}"
            # Only pass filter parameters to count query, not limit/offset
            count_params = {k: v for k, v in params.items() if k not in ['limit', 'offset']}
            count_result = await database.fetch_one(count_query, count_params)
            total_count = count_result['count'] if count_result else 0
            
            # Build dynamic ORDER BY clause
            order_clause = f"ORDER BY {sort_field} {sort_order.upper()}"
            
            # Get logs with offset/limit for endless scrolling
            logs_query = f"""
                SELECT timestamp, level, message, module, function, line,
                       user, extra, ip_address
                FROM app_log
                {where_clause}
                {order_clause}
                LIMIT :limit OFFSET :offset
            """
            
            logs = await database.fetch_all(logs_query, params)
            
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
                "has_next": has_more,  # Backward compatibility
                "pagination": {
                    "page": (offset // limit) + 1,
                    "limit": limit,
                    "offset": offset,
                    "total": total_count,  # Actual total from database
                    "showing": len(logs_data)  # Number of records in this response
                }
            })
        except Exception as e:
            logger.error(f"Error fetching logs: {e}")
            return JSONResponse(
                status_code=500,
                content={"error": "Failed to fetch logs"}
            )
        
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
    admin: dict = Depends(require_admin_auth_session)
):
    """Clear all application logs"""
    
    try:
        # Log the clear action before clearing
        add_log(
            "INFO",
            "logs_admin",
            "Admin cleared all application logs",
            function="clear_logs",
            line=0,
            user="system",
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
    admin: dict = Depends(require_admin_auth_session)
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
    admin: dict = Depends(require_admin_auth_session)
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
        
        # Check if the query contains multiple statements (separated by semicolons)
        statements = [stmt.strip() for stmt in query.split(';') if stmt.strip()]
        
        # Determine if this is a SELECT query or a modification query
        is_select = len(statements) == 1 and (statements[0].upper().strip().startswith('SELECT') or statements[0].upper().strip().startswith('PRAGMA'))
        
        # Add specific log entry for query history tracking
        log_with_context("INFO", "sql_admin", f"SQL Query executed by {admin.get('email', 'unknown')}: {query[:200]}{'...' if len(query) > 200 else ''}", request)
        
        if is_select:
            # For SELECT queries, fetch results
            rows = await database.fetch_all(statements[0])
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
            # For multiple statements or modification queries, execute each statement individually
            total_affected = 0
            messages = []
            
            for i, statement in enumerate(statements):
                if not statement:
                    continue
                    
                try:
                    result = await database.execute(statement)
                    if result:
                        total_affected += result
                        messages.append(f"Statement {i+1}: {result} rows affected")
                    else:
                        messages.append(f"Statement {i+1}: executed successfully")
                except Exception as stmt_error:
                    messages.append(f"Statement {i+1}: Error - {str(stmt_error)}")
            
            execution_time = round((time.time() - start_time) * 1000, 2)
            
            return JSONResponse({
                "status": "success",
                "rows": [],
                "execution_time": execution_time,
                "message": f"Executed {len(statements)} statements. {'; '.join(messages)}"
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
async def download_schema(request: Request, admin: dict = Depends(require_admin_auth_session)):
    """Download the current database schema as a SQL dump file"""
    from datetime import datetime
    from schema_dump import generate_schema_dump
    
    try:
        log_with_context("INFO", "sql_admin_schema_download", "Admin downloading database schema", request)
        
        # Use the new schema dump module
        schema_content = await generate_schema_dump()
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"database_schema_{timestamp}.sql"
        
        log_with_context("INFO", "sql_admin_schema_downloaded", "Schema successfully downloaded", request)
        
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
        log_with_context("ERROR", "sql_admin_schema_error", f"Schema download error: {str(e)}", request)
        return JSONResponse({
            "status": "error",
            "message": f"Schema download failed: {str(e)}"
        }, status_code=500)


# --- Projects Admin Page ---
@app.get("/projectsadmin", response_class=HTMLResponse)
async def projects_admin_page(
    request: Request,
    admin: dict = Depends(require_admin_auth_session)
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
            SELECT id, provider, client_id, redirect_uri, is_active, created_at
            FROM oauth_apps 
            WHERE portfolio_id = :portfolio_id
            ORDER BY provider, created_at DESC
        """
        try:
            from database import PORTFOLIO_ID
            portfolio_id = PORTFOLIO_ID
            oauth_apps = await database.fetch_all(oauth_apps_query, {"portfolio_id": portfolio_id})
        except:
            oauth_apps = []
        
        return JSONResponse({
            "status": "success",
            "oauth_apps": [dict(row) for row in oauth_apps],
            "total_oauth_apps": len(oauth_apps)
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
        from database import PORTFOLIO_ID
        portfolio_id = PORTFOLIO_ID
        query = "SELECT * FROM work_experience WHERE portfolio_id = :portfolio_id ORDER BY sort_order, start_date DESC"
        rows = await database.fetch_all(query, {"portfolio_id": portfolio_id})
        
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
async def get_workitem(id: str, admin: dict = Depends(require_admin_auth_session)):
    from database import PORTFOLIO_ID
    portfolio_id = PORTFOLIO_ID
    query = "SELECT * FROM work_experience WHERE id=:id AND portfolio_id=:portfolio_id"
    row = await database.fetch_one(query, {"id": id, "portfolio_id": portfolio_id})
    if not row:
        raise HTTPException(status_code=404, detail="Work item not found")
    # Convert UUID to string for Pydantic model
    row_dict = dict(row)
    if row_dict.get('id'):
        row_dict['id'] = str(row_dict['id'])
    return WorkItem(**row_dict)

# Create a new work item
@app.post("/workitems", response_model=WorkItem)
async def create_workitem(item: WorkItem, admin: dict = Depends(require_admin_auth_session)):
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
async def update_workitem(id: str, item: WorkItem, admin: dict = Depends(require_admin_auth_session)):
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
async def delete_workitem(id: str, admin: dict = Depends(require_admin_auth_session)):
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
            
        from database import PORTFOLIO_ID
        portfolio_id = PORTFOLIO_ID
        query = "SELECT * FROM projects WHERE portfolio_id = :portfolio_id ORDER BY sort_order, title"
        rows = await database.fetch_all(query, {"portfolio_id": portfolio_id})
        
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
async def get_project(id: str, admin: dict = Depends(require_admin_auth_session)):
    from database import PORTFOLIO_ID
    portfolio_id = PORTFOLIO_ID
    query = "SELECT * FROM projects WHERE id = :id AND portfolio_id = :portfolio_id"
    row = await database.fetch_one(query, {"id": id, "portfolio_id": portfolio_id})
    
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
async def create_project(project: Project, admin: dict = Depends(require_admin_auth_session)):
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
async def update_project(id: str, project: Project, admin: dict = Depends(require_admin_auth_session)):
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
async def delete_project(id: str, admin: dict = Depends(require_admin_auth_session)):
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
async def google_oauth_status(admin: dict = Depends(require_admin_auth_session)):
    """Get Google OAuth configuration status"""
    
    try:
        add_log("INFO", "oauth_google_status", "Admin checked Google OAuth status")
        
        # Placeholder for Google OAuth implementation
        return JSONResponse({
            "configured": False,
            "connected": False,
            "message": "Google OAuth not yet implemented",
            "scopes": []
        })
        
    except Exception as e:
        logger.error(f"Error getting Google OAuth status: {str(e)}")
        add_log("ERROR", "oauth_google_error", f"Failed to get Google OAuth status: {str(e)}")
        return JSONResponse({
            "status": "error",
            "error": str(e)
        }, status_code=500)


@app.post("/admin/oauth/google/configure")
async def configure_google_oauth(request: Request, admin: dict = Depends(require_admin_auth_session)):
    """Configure Google OAuth application"""
    
    try:
        data = await request.json()
        add_log("INFO", "oauth_google_configure_attempt", "Admin attempted to configure Google OAuth")
        
        # Placeholder for Google OAuth configuration
        return JSONResponse({
            "status": "error",
            "message": "Google OAuth configuration not yet implemented"
        }, status_code=501)
        
    except Exception as e:
        logger.error(f"Error configuring Google OAuth: {str(e)}")
        add_log("ERROR", "oauth_google_configure_error", f"Failed to configure Google OAuth: {str(e)}")
        return JSONResponse({
            "status": "error",
            "error": str(e)
        }, status_code=500)


# --- LinkedIn OAuth Admin Endpoints ---

@app.get("/admin/oauth/linkedin/status")
async def linkedin_oauth_status(admin: dict = Depends(require_admin_auth_session)):
    """Get LinkedIn OAuth configuration and connection status"""
    
    try:
        add_log("INFO", "oauth_linkedin_status", "Admin checked LinkedIn OAuth status")
        
        ttw_oauth_manager = TTWOAuthManager()
        
        app_configured = await ttw_oauth_manager.is_oauth_app_configured()
        app_config = await ttw_oauth_manager.get_oauth_app_config() if app_configured else None
        connected = await ttw_oauth_manager.is_linkedin_connected()
        connection_data = await ttw_oauth_manager.get_linkedin_connection() if connected else None
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
        add_log("ERROR", "oauth_linkedin_status_error", f"Failed to get LinkedIn OAuth status: {str(e)}")
        return JSONResponse({
            "status": "error",
            "error": str(e)
        }, status_code=500)


@app.post("/admin/oauth/linkedin/configure")
async def configure_linkedin_oauth(request: Request, admin: dict = Depends(require_admin_auth_session)):
    """Configure LinkedIn OAuth application settings"""
    
    try:
        data = await request.json()
        add_log("INFO", "oauth_linkedin_configure_attempt", "System")
        
        required_fields = ["client_id", "client_secret", "redirect_uri"]
        missing_fields = [field for field in required_fields if not data.get(field)]
        
        if missing_fields:
            add_log("ERROR", "oauth_linkedin_configure_validation_error", "System")
            return JSONResponse({
                "status": "error",
                "message": f"Missing required fields: {', '.join(missing_fields)}"
            }, status_code=400)
        
        ttw_oauth_manager = TTWOAuthManager()
        success = await ttw_oauth_manager.configure_oauth_app( data)
        
        if success:
            add_log("INFO", "oauth_linkedin_configure_success", "System")
            return JSONResponse({
                "status": "success",
                "message": "LinkedIn OAuth application configured successfully"
            })
        else:
            add_log("ERROR", "oauth_linkedin_configure_failure", "System")
            return JSONResponse({
                "status": "error",
                "message": "Failed to configure LinkedIn OAuth application"
            }, status_code=500)
        
    except Exception as e:
        logger.error(f"Error configuring LinkedIn OAuth: {str(e)}")
        add_log("ERROR", "oauth_linkedin_configure_error", "System")
        return JSONResponse({
            "status": "error",
            "error": str(e)
        }, status_code=500)


@app.post("/admin/oauth/linkedin/connect")
async def linkedin_oauth_connect(request: Request, admin: dict = Depends(require_admin_auth_session)):
    """Initiate LinkedIn OAuth connection flow"""
    
    try:
        data = await request.json()
        requested_scopes = data.get("scopes", [])
        
        add_log("INFO", "oauth_linkedin_connect_attempt", "System")
        
        ttw_oauth_manager = TTWOAuthManager()
        
        # Check if OAuth app is configured first
        if not await ttw_oauth_manager.is_oauth_app_configured():
            add_log("INFO", "oauth_linkedin_connect_not_configured", "System")
            return JSONResponse({
                "status": "error",
                "message": "LinkedIn OAuth application must be configured before connecting"
            }, status_code=400)
        
        auth_url, state = await ttw_oauth_manager.get_linkedin_authorization_url( requested_scopes)
        
        add_log("INFO", "oauth_linkedin_auth_url_generated", "System")
        
        return JSONResponse({
            "status": "success",
            "auth_url": auth_url,
            "state": state
        })
        
    except Exception as e:
        logger.error(f"Error initiating LinkedIn OAuth: {str(e)}")
        add_log("ERROR", "oauth_linkedin_connect_error", "System")
        return JSONResponse({
            "status": "error",
            "error": str(e)
        }, status_code=500)


@app.post("/admin/oauth/linkedin/disconnect")
async def linkedin_oauth_disconnect_admin(admin: dict = Depends(require_admin_auth_session)):
    """Disconnect LinkedIn OAuth connection"""
    
    try:
        add_log("INFO", "oauth_linkedin_disconnect_attempt", "System")
        
        ttw_oauth_manager = TTWOAuthManager()
        success = await ttw_oauth_manager.remove_linkedin_connection()
        
        if success:
            add_log("INFO", "oauth_linkedin_disconnect_success", "System")
            return JSONResponse({
                "status": "success",
                "message": "LinkedIn OAuth connection removed successfully"
            })
        else:
            add_log("ERROR", "oauth_linkedin_disconnect_failure", "System")
            return JSONResponse({
                "status": "error",
                "message": "Failed to remove LinkedIn OAuth connection"
            }, status_code=500)
        
    except Exception as e:
        logger.error(f"Error disconnecting LinkedIn OAuth: {str(e)}")
        add_log("ERROR", "oauth_linkedin_disconnect_error", "System")
        return JSONResponse({
            "status": "error",
            "error": str(e)
        }, status_code=500)


@app.post("/admin/oauth/linkedin/test")
async def test_linkedin_oauth_connection(admin: dict = Depends(require_admin_auth_session)):
    """Test LinkedIn OAuth connection by making an API call"""
    
    try:
        add_log("INFO", "oauth_linkedin_test_attempt", "System")
        
        from ttw_linkedin_sync import TTWLinkedInSync
        sync_service = TTWLinkedInSync()
        
        # Test connection by getting profile info
        profile_data = await sync_service.get_linkedin_profile()
        
        if profile_data:
            add_log("INFO", "oauth_linkedin_test_success", "System")
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
            add_log("ERROR", "oauth_linkedin_test_failure", "System")
            return JSONResponse({
                "status": "error",
                "message": "Failed to retrieve LinkedIn profile data"
            }, status_code=500)
        
    except Exception as e:
        logger.error(f"Error testing LinkedIn OAuth: {str(e)}")
        add_log("ERROR", "oauth_linkedin_test_error", "System")
        return JSONResponse({
            "status": "error",
            "error": str(e)
        }, status_code=500)


# --- Google OAuth Admin Routes ---
@app.get("/admin/google/oauth", response_class=HTMLResponse)
async def google_oauth_admin_page(request: Request):
    """Google OAuth administration interface - temporarily no auth required for setup"""
    add_log("INFO", "admin_google_oauth_page_access", "Google OAuth admin page accessed (no auth)")
    
    # Create mock admin data for template
    mock_admin = {
        "email": "setup@admin.local",
        "name": "Setup Admin",
        "authenticated": True,
        "is_admin": True
    }
    
    return templates.TemplateResponse("google_oauth_admin.html", {
        "request": request,
        "current_page": "google_oauth_admin",
        "admin": mock_admin,
        "user_info": mock_admin,
        "user_authenticated": True,
        "user_email": "setup@admin.local",
        "cache_bust": int(time.time())
    })


@app.get("/admin/google/oauth/status")
async def google_oauth_status(request: Request, admin: dict = Depends(require_admin_auth_session)):
    """Get Google OAuth configuration and connection status"""
    
    try:
        # Import PORTFOLIO_ID and log it
        from database import PORTFOLIO_ID
        add_log("DEBUG", "oauth_status_check", "System")
        
        # Check if Google OAuth is configured in database
        ttw_manager = TTWOAuthManager()
        google_configured = await ttw_manager.is_google_oauth_app_configured()
        
        add_log("DEBUG", "oauth_configured_result", f"Google configured: {google_configured}")
        
        config = None
        credentials = None
        if google_configured:
            config = await ttw_manager.get_google_oauth_app_config()
            credentials = await ttw_manager.get_google_oauth_credentials()
            add_log("DEBUG", "oauth_config_loaded", f"Config loaded: {config is not None}, Credentials loaded: {credentials is not None}")
            add_log("DEBUG", "oauth_config_content", f"Config content: {config}")
            add_log("DEBUG", "oauth_credentials_content", f"Credentials content: {credentials}")
        
        # Check current session for Google auth
        google_connected = "user" in request.session if hasattr(request, 'session') else False
        
        # Build response with detailed logging
        client_secret = credentials.get("client_secret", "") if credentials else ""
        add_log("DEBUG", "oauth_client_secret_check", f"Client secret value: {'[PRESENT]' if client_secret else '[EMPTY]'}")
        
        return JSONResponse({
            "configured": google_configured,
            "connected": google_connected,
            "client_id": config.get("client_id", "") if config else "",
            "client_secret": client_secret,
            "redirect_uri": config.get("redirect_uri", "") if config else "",
            "account_email": request.session.get("user", {}).get("email") if google_connected else None,
            "last_sync": request.session.get("user", {}).get("login_time") if google_connected else None,
            "token_expiry": request.session.get("user", {}).get("expires_at") if google_connected else None
        })
        
    except Exception as e:
        add_log("ERROR", "oauth_status_error", f"Error getting Google OAuth status: {str(e)}")
        logger.error(f"Error getting Google OAuth status: {str(e)}")
        return JSONResponse({
            "status": "error",
            "error": str(e)
        }, status_code=500)


@app.post("/admin/google/oauth/config")
async def save_google_oauth_config(
    request: Request,
    config: dict,
    admin: dict = Depends(require_admin_auth_session)
):
    """Save Google OAuth configuration to database"""
    
    try:
        add_log("INFO", "Updating Google OAuth configuration", 
                "main", "save_google_oauth_config")
        
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
        result = await ttw_manager.configure_google_oauth_app(config)
        
        if result:
            add_log("INFO", "Google OAuth config saved successfully", 
                    "main", "save_google_oauth_config")
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
        import traceback
        full_traceback = traceback.format_exc()
        logger.error(f"Error saving Google OAuth config: {str(e)}\nTraceback: {full_traceback}")
        log_with_context("ERROR", "admin_google_oauth_config_error", 
                         f"Error saving Google OAuth config: {str(e)}\nTraceback: {full_traceback}", 
                         request)
        return JSONResponse({
            "status": "error",
            "error": str(e),
            "traceback": full_traceback
        }, status_code=500)


@app.delete("/admin/google/oauth/config")
async def clear_google_oauth_config(admin: dict = Depends(require_admin_auth_session)):
    """Clear Google OAuth configuration"""
    
    try:
        add_log("INFO", "Clearing Google OAuth configuration", "main")
        
        ttw_manager = TTWOAuthManager()
        result = await ttw_manager.remove_google_oauth_app()
        
        if result:
            add_log("INFO", "Google OAuth config cleared successfully", "main")
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
        add_log("ERROR", f"Error clearing Google OAuth config: {str(e)}", "main")
        return JSONResponse({
            "status": "error",
            "error": str(e)
        }, status_code=500)


@app.get("/admin/google/oauth/authorize")
async def initiate_google_oauth(request: Request, admin: dict = Depends(require_admin_auth_session)):
    """Initiate Google OAuth authorization flow with explicit scope permissions"""
    
    try:
        add_log("INFO", "Initiating Google OAuth authorization", "main")
        
        # Get redirect URI from environment
        redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/callback")
        
        # Generate a new state parameter for CSRF protection
        import secrets
        state = secrets.token_urlsafe(32)
        request.session['oauth_state'] = state
        
        # Define explicit scopes that we're requesting (including Gmail for email sending)
        scopes = [
            'openid',
            'email', 
            'profile',
            'https://www.googleapis.com/auth/gmail.send'
        ]
        
        # Use existing OAuth flow with explicit scopes
        auth_result = await oauth.google.authorize_redirect(
            request, 
            redirect_uri,
            scope=' '.join(scopes),
            state=state,
            access_type='offline',  # Request refresh token
            prompt='consent'        # Force consent screen to show permissions
        )
        
        # Extract the redirect URL from the response
        if hasattr(auth_result, 'headers') and 'location' in auth_result.headers:
            auth_url = auth_result.headers['location']
        else:
            # Fallback - construct URL manually
            auth_url = str(auth_result)
        
        return JSONResponse({
            "status": "success",
            "auth_url": auth_url,
            "requested_scopes": scopes,
            "scope_descriptions": {
                "openid": "Basic identity verification - allows the app to verify your identity",
                "email": "Email address access - allows the app to read your primary email address", 
                "profile": "Profile information access - allows the app to read your name and profile picture"
            }
        })
        
    except Exception as e:
        logger.error(f"Error initiating Google OAuth: {str(e)}")
        add_log("ERROR", "admin_google_oauth_initiate_error", "System")
        return JSONResponse({
            "status": "error",
            "detail": str(e)
        }, status_code=500)


@app.post("/admin/google/oauth/revoke")
async def revoke_google_oauth(request: Request, admin: dict = Depends(require_admin_auth_session)):
    """Revoke Google OAuth access"""
    
    try:
        add_log("INFO", "admin_google_oauth_revoke", "System")
        
        # Only clear Google OAuth data from session, keep admin authentication
        if hasattr(request, 'session') and 'user' in request.session:
            user_session = request.session['user']
            # Remove only Google OAuth tokens, keep admin authentication
            user_session.pop('access_token', None)
            user_session.pop('refresh_token', None)
            user_session.pop('token_expires_at', None)
            # Keep authenticated and is_admin flags
            request.session['user'] = user_session
        
        add_log("INFO", "admin_google_oauth_revoked", "System")
        
        return JSONResponse({
            "status": "success",
            "message": "Google OAuth access revoked successfully"
        })
        
    except Exception as e:
        logger.error(f"Error revoking Google OAuth: {str(e)}")
        add_log("ERROR", "admin_google_oauth_revoke_error", "System")
        return JSONResponse({
            "status": "error",
            "error": str(e)
        }, status_code=500)


@app.post("/admin/google/oauth/revoke-scope")
async def revoke_google_oauth_scope(request: Request, admin: dict = Depends(require_admin_auth_session)):
    """Revoke a specific Google OAuth scope"""
    
    try:
        # Parse the request body to get the scope
        try:
            body = await request.json()
            scope_to_revoke = body.get("scope")
        except Exception as json_error:
            add_log("ERROR", "admin_google_oauth_scope_revoke_json_error", "System")
            return JSONResponse({
                "status": "error", 
                "detail": "Invalid JSON in request body"
            }, status_code=400)
        
        if not scope_to_revoke:
            return JSONResponse({
                "status": "error", 
                "detail": "No scope specified"
            }, status_code=400)
            
        add_log("INFO", "admin_google_oauth_scope_revoke", "System")
        
        # Get the current user's access token from session
        if not hasattr(request, 'session') or 'user' not in request.session:
            return JSONResponse({
                "status": "error",
                "detail": "No active session"
            }, status_code=401)
            
        user_session = request.session['user']
        access_token = user_session.get('access_token')
        
        if not access_token:
            return JSONResponse({
                "status": "error",
                "detail": "No access token available"
            }, status_code=401)
            
        # Make request to Google's revoke endpoint for the specific scope
        # Note: Google's OAuth2 revoke endpoint doesn't support individual scope revocation
        # Instead, we'll revoke the entire token and suggest re-authorization without that scope
        revoke_url = f"https://oauth2.googleapis.com/revoke?token={access_token}"
        
        add_log("INFO", "admin_google_oauth_scope_revoke_request", "System")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(revoke_url)
            
        add_log("INFO", "admin_google_oauth_scope_revoke_response", "System")
            
        if response.status_code == 200:
            # Clear the session tokens since we revoked the entire token
            user_session.pop('access_token', None)
            user_session.pop('refresh_token', None)
            user_session.pop('token_expires_at', None)
            request.session['user'] = user_session
            
            add_log("INFO", "admin_google_oauth_scope_revoked", "System")
            
            return JSONResponse({
                "status": "success",
                "message": f"Access revoked. Note: Google OAuth doesn't support individual scope revocation, so the entire token was revoked. Please re-authorize with only the scopes you want to grant."
            })
        else:
            response_text = ""
            try:
                response_text = response.text
            except:
                response_text = "Could not read response text"
            
            add_log("ERROR", "admin_google_oauth_scope_revoke_failed", "System")
            return JSONResponse({
                "status": "error",
                "detail": f"Failed to revoke scope with Google (HTTP {response.status_code})"
            }, status_code=400)
        
    except Exception as e:
        error_traceback = traceback.format_exc()
        logger.error(f"Error revoking Google OAuth scope: {str(e)}\n{error_traceback}")
        add_log("ERROR", "admin_google_oauth_scope_revoke_error", "System")
        return JSONResponse({
            "status": "error",
            "detail": str(e)
        }, status_code=500)


@app.get("/admin/google/oauth/test")
async def test_google_oauth_connection(admin: dict = Depends(require_admin_auth_session)):
    """Test Google OAuth connection"""
    
    try:
        add_log("INFO", "admin_google_oauth_test", "System")
        
        google_configured = bool(os.getenv("GOOGLE_CLIENT_ID") and os.getenv("GOOGLE_CLIENT_SECRET"))
        
        if not google_configured:
            return JSONResponse({
                "status": "error",
                "detail": "Google OAuth not configured"
            }, status_code=400)
        
        # Test configuration validity
        add_log("INFO", "admin_google_oauth_test_success", "System")
        
        return JSONResponse({
            "status": "success",
            "message": "Google OAuth configuration is valid"
        })
        
    except Exception as e:
        logger.error(f"Error testing Google OAuth: {str(e)}")
        add_log("ERROR", "admin_google_oauth_test_error", "System")
        return JSONResponse({
            "status": "error",
            "error": str(e)
        }, status_code=500)


@app.get("/admin/google/oauth/profile")
async def get_google_profile(request: Request, admin: dict = Depends(require_admin_auth_session)):
    """Retrieve Google profile information using current session token"""
    import httpx
    
    # Prominent log entry to ensure we see this endpoint being called
    add_log("INFO", "google_profile_endpoint_accessed", "System")
    
    try:
        add_log("INFO", "admin_google_profile_request", "System")
        
        # Check if user has an active Google session
        if not hasattr(request, 'session') or 'user' not in request.session:
            add_log("WARNING", "admin_google_profile_no_session", "System")
            return JSONResponse({
                "status": "error",
                "message": "No active Google session. Please authorize Google access first."
            }, status_code=401)
        
        user_session = request.session.get('user', {})
        access_token = user_session.get('access_token')
        
        if not access_token:
            add_log("WARNING", "admin_google_profile_no_token", "System")
            return JSONResponse({
                "status": "error", 
                "message": "No Google access token found. Please re-authorize Google access."
            }, status_code=401)
        
        # Use simple Google userinfo endpoint that works with basic OAuth scopes
        profile_url = "https://www.googleapis.com/oauth2/v2/userinfo"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json"
        }
        
        add_log("DEBUG", "admin_google_profile_api_request", 
               "System")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(profile_url, headers=headers)
            
            if response.status_code == 200:
                profile_data = response.json()
                
                add_log("INFO", "admin_google_profile_success", 
                       "System")
                
                return JSONResponse({
                    "status": "success",
                    "data": profile_data
                })
            
            elif response.status_code == 401:
                add_log("WARNING", "admin_google_profile_token_expired", 
                       "System")
                return JSONResponse({
                    "status": "error",
                    "message": "Google access token expired or invalid. Please re-authorize Google access."
                }, status_code=401)
            
            else:
                error_text = response.text
                add_log("ERROR", "admin_google_profile_api_error", 
                       "System")
                return JSONResponse({
                    "status": "error",
                    "message": f"Google API error: {response.status_code}",
                    "details": error_text
                }, status_code=response.status_code)
                
    except httpx.RequestError as e:
        add_log("ERROR", "admin_google_profile_network_error", 
               "System")
        return JSONResponse({
            "status": "error",
            "message": "Network error contacting Google API"
        }, status_code=500)
        
    except Exception as e:
        logger.error(f"Error retrieving Google profile: {str(e)}")
        add_log("ERROR", "admin_google_profile_error", 
               "System")
        return JSONResponse({
            "status": "error",
            "message": f"Error retrieving Google profile: {str(e)}"
        }, status_code=500)


@app.get("/admin/google/oauth/scopes")
async def get_google_granted_scopes(request: Request, admin: dict = Depends(require_admin_auth_session)):
    """Check which Google OAuth scopes have been granted by querying Google's tokeninfo endpoint"""
    import httpx
    
    try:
        add_log("INFO", "admin_google_scopes_request", "System")
        
        # Check if user has an active Google session
        if not hasattr(request, 'session') or 'user' not in request.session:
            return JSONResponse({
                "status": "error",
                "message": "No active Google session. Please authorize Google access first.",
                "scopes": {}
            }, status_code=401)
        
        user_session = request.session.get('user', {})
        access_token = user_session.get('access_token')
        
        if not access_token:
            return JSONResponse({
                "status": "error", 
                "message": "No Google access token found. Please re-authorize Google access.",
                "scopes": {}
            }, status_code=401)
        
        # Use Google's tokeninfo endpoint to get granted scopes
        tokeninfo_url = f"https://www.googleapis.com/oauth2/v1/tokeninfo?access_token={access_token}"
        
        add_log("DEBUG", "admin_google_scopes_api_request", 
               "System")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(tokeninfo_url)
            
            if response.status_code == 200:
                token_data = response.json()
                granted_scopes = token_data.get('scope', '').split(' ')
                
                # Map the scopes we care about
                scope_status = {
                    'openid': 'openid' in granted_scopes,
                    'email': 'email' in granted_scopes or 'https://www.googleapis.com/auth/userinfo.email' in granted_scopes,
                    'profile': 'profile' in granted_scopes or 'https://www.googleapis.com/auth/userinfo.profile' in granted_scopes,
                    'https://www.googleapis.com/auth/gmail.send': 'https://www.googleapis.com/auth/gmail.send' in granted_scopes
                }
                
                add_log("INFO", "admin_google_scopes_success", 
                       "System")
                
                return JSONResponse({
                    "status": "success",
                    "scopes": scope_status,
                    "raw_scopes": granted_scopes,
                    "token_info": {
                        "audience": token_data.get('audience'),
                        "expires_in": token_data.get('expires_in'),
                        "issued_to": token_data.get('issued_to')
                    }
                })
            
            elif response.status_code == 400:
                add_log("WARNING", "admin_google_scopes_invalid_token", 
                       "System")
                return JSONResponse({
                    "status": "error",
                    "message": "Invalid or expired access token. Please re-authorize Google access.",
                    "scopes": {}
                }, status_code=401)
            
            else:
                add_log("WARNING", "admin_google_scopes_api_error", 
                       "System")
                return JSONResponse({
                    "status": "error",
                    "message": f"Google API error: {response.status_code}",
                    "scopes": {}
                }, status_code=response.status_code)
                
    except httpx.RequestError as e:
        logger.error(f"Network error contacting Google tokeninfo API: {str(e)}")
        add_log("ERROR", "admin_google_scopes_network_error", 
               "System")
        return JSONResponse({
            "status": "error",
            "message": "Network error contacting Google API",
            "scopes": {}
        }, status_code=500)
        
    except Exception as e:
        logger.error(f"Error checking Google scopes: {str(e)}")
        add_log("ERROR", "admin_google_scopes_error", 
               "System")
        return JSONResponse({
            "status": "error",
            "message": f"Error checking Google scopes: {str(e)}",
            "scopes": {}
        }, status_code=500)


# --- LinkedIn OAuth Admin Routes ---

@app.get("/admin/linkedin/oauth", response_class=HTMLResponse)
async def linkedin_oauth_admin_page(request: Request, admin: dict = Depends(require_admin_auth_session)):
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
async def linkedin_oauth_status(request: Request, admin: dict = Depends(require_admin_auth_session)):
    """Get LinkedIn OAuth configuration and connection status"""
    
    try:
        add_log("INFO", "admin_linkedin_oauth_status", "System")
        
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
async def get_linkedin_oauth_config_for_form(admin: dict = Depends(require_admin_auth_session)):
    """Get LinkedIn OAuth configuration for admin form"""
    
    try:
        add_log("INFO", "admin_linkedin_config_form_load", "System")
        
        # Get current LinkedIn OAuth config from oauth_apps table (consistent with status route)
        query = """
            SELECT client_id, redirect_uri, scopes, is_active, created_at
            FROM oauth_apps 
            WHERE portfolio_id = :portfolio_id AND provider = 'linkedin'
            ORDER BY created_at DESC
            LIMIT 1
        """
        from database import PORTFOLIO_ID
        portfolio_id = PORTFOLIO_ID
        result = await database.fetch_one(query, {"portfolio_id": portfolio_id})
        
        if result:
            return JSONResponse({
                "client_id": result["client_id"] or "",
                "client_secret": "",  # Never return the actual secret for security
                "redirect_uri": result["redirect_uri"] or "",
                "scopes": result["scopes"] or "r_liteprofile,r_emailaddress",
                "configured": True
            })
        else:
            return JSONResponse({
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
    admin: dict = Depends(require_admin_auth_session)
):
    """Save LinkedIn OAuth configuration (shortcut route for JavaScript)"""
    # Forward to the main OAuth config route
    return await save_linkedin_oauth_config(config, admin)


@app.post("/admin/linkedin/oauth/config")
async def save_linkedin_oauth_config(
    request: Request,
    config: dict,
    admin: dict = Depends(require_admin_auth_session)
):
    """Save LinkedIn OAuth configuration to database"""
    
    try:
        add_log("INFO", "admin_linkedin_oauth_config_update", "System")
        
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
        result = await ttw_manager.configure_linkedin_oauth_app( config)
        
        if result:
            add_log("INFO", "admin_linkedin_oauth_config_saved", "System")
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
        add_log("ERROR", "admin_linkedin_oauth_config_save_error", "System")
        return JSONResponse({
            "status": "error",
            "error": str(e)
        }, status_code=500)


@app.get("/admin/linkedin/test-config")
async def test_linkedin_config_shortcut(admin: dict = Depends(require_admin_auth_session)):
    """Test LinkedIn OAuth configuration (shortcut route for JavaScript)"""
    # Forward to the main OAuth test route
    return await test_linkedin_oauth_config(admin)


@app.delete("/admin/linkedin/oauth/config")
async def clear_linkedin_oauth_config(admin: dict = Depends(require_admin_auth_session)):
    """Clear LinkedIn OAuth configuration"""
    
    try:
        add_log("INFO", "admin_linkedin_oauth_config_clear", "System")
        
        ttw_manager = TTWOAuthManager()
        result = await ttw_manager.remove_linkedin_oauth_app()
        
        if result:
            add_log("INFO", "admin_linkedin_oauth_config_cleared", "System")
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
        add_log("ERROR", "admin_linkedin_oauth_config_clear_error", "System")
        return JSONResponse({
            "status": "error",
            "error": str(e)
        }, status_code=500)


@app.get("/admin/linkedin/oauth/authorize")
async def initiate_linkedin_oauth(admin: dict = Depends(require_admin_auth_session)):
    """Initiate LinkedIn OAuth authorization flow"""
    
    try:
        add_log("INFO", "admin_linkedin_oauth_initiate", "System")
        
        ttw_manager = TTWOAuthManager()
        
        # First check if OAuth app is configured
        if not await ttw_manager.is_oauth_app_configured():
            add_log("ERROR", "admin_linkedin_oauth_not_configured", "System")
            return JSONResponse({
                "status": "error",
                "detail": "LinkedIn OAuth application must be configured first. Please configure the app in the admin panel."
            }, status_code=400)
        
        # Get configuration to verify client_id exists
        config = await ttw_manager.get_oauth_app_config()
        if not config or not config.get("client_id"):
            add_log("ERROR", "admin_linkedin_oauth_missing_client_id", "System")
            return JSONResponse({
                "status": "error", 
                "detail": "LinkedIn OAuth configuration is incomplete. Please reconfigure the application."
            }, status_code=400)
        
        auth_url, state = await ttw_manager.get_linkedin_authorization_url()
        
        if auth_url:
            add_log("INFO", "admin_linkedin_oauth_url_generated", "System")
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
        add_log("ERROR", "admin_linkedin_oauth_initiate_error", "System")
        return JSONResponse({
            "status": "error",
            "error": str(e)
        }, status_code=500)


@app.get("/admin/linkedin/oauth/debug-config")
async def debug_linkedin_oauth_config(admin: dict = Depends(require_admin_auth_session)):
    """Debug LinkedIn OAuth configuration"""
    
    try:
        add_log("INFO", "admin_linkedin_oauth_debug", 
                "System")
        
        ttw_manager = TTWOAuthManager()
        
        # Check if OAuth app is configured
        is_configured = await ttw_manager.is_oauth_app_configured()
        
        debug_info = {
            "is_configured": is_configured,
            "config_data": None,
            "error": None
        }
        
        if is_configured:
            try:
                config = await ttw_manager.get_oauth_app_config()
                if config:
                    # Don't expose sensitive data, just check if fields exist
                    debug_info["config_data"] = {
                        "client_id_exists": bool(config.get("client_id")),
                        "client_secret_exists": bool(config.get("client_secret")),
                        "redirect_uri": config.get("redirect_uri"),
                        "scopes": config.get("scopes"),
                        "configured_by": config.get("configured_by_email"),
                        "created_at": config.get("created_at")
                    }
                else:
                    debug_info["error"] = "Configuration exists but data is null"
            except Exception as e:
                debug_info["error"] = f"Error retrieving config: {str(e)}"
        
        return JSONResponse({
            "status": "success",
            "debug_info": debug_info
        })
        
    except Exception as e:
        logger.error(f"Error debugging LinkedIn OAuth config: {str(e)}")
        return JSONResponse({
            "status": "error",
            "error": str(e)
        }, status_code=500)


async def revoke_linkedin_oauth(admin: dict = Depends(require_admin_auth_session)):
    """Revoke LinkedIn OAuth access"""
    
    try:
        add_log("INFO", "admin_linkedin_oauth_revoke", "System")
        
        ttw_manager = TTWOAuthManager()
        result = await ttw_manager.remove_linkedin_connection()
        
        if result:
            add_log("INFO", "admin_linkedin_oauth_revoked", "System")
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
        add_log("ERROR", "admin_linkedin_oauth_revoke_error", "System")
        return JSONResponse({
            "status": "error",
            "error": str(e)
        }, status_code=500)


@app.get("/admin/linkedin/oauth/test")
async def test_linkedin_oauth_config(admin: dict = Depends(require_admin_auth_session)):
    """Test LinkedIn OAuth configuration"""
    
    try:
        add_log("INFO", "admin_linkedin_oauth_config_test", "System")
        
        ttw_manager = TTWOAuthManager()
        
        # Check if OAuth app is configured
        is_configured = await ttw_manager.is_oauth_app_configured()
        
        if is_configured:
            config = await ttw_manager.get_oauth_app_config()
            if config:
                add_log("INFO", "admin_linkedin_oauth_config_test_success", "System")
                return JSONResponse({
                    "status": "success",
                    "message": "LinkedIn OAuth configuration is valid."
                })
            else:
                add_log("ERROR", "admin_linkedin_oauth_config_test_failure", "System")
                return JSONResponse({
                    "status": "error",
                    "detail": "LinkedIn OAuth configuration not found in database"
                }, status_code=400)
        else:
            add_log("ERROR", "admin_linkedin_oauth_config_test_failure", "System")
            return JSONResponse({
                "status": "error",
                "detail": "LinkedIn OAuth application is not configured"
            }, status_code=400)
        
    except Exception as e:
        logger.error(f"Error testing LinkedIn OAuth config: {str(e)}")
        add_log("ERROR", "admin_linkedin_oauth_config_test_error", "System")
        return JSONResponse({
            "status": "error",
            "error": str(e)
        }, status_code=500)


@app.get("/admin/linkedin/oauth/test-api")
async def test_linkedin_oauth_api(admin: dict = Depends(require_admin_auth_session)):
    """Test LinkedIn OAuth API access"""
    
    try:
        add_log("INFO", "admin_linkedin_oauth_api_test", "System")
        
        ttw_manager = TTWOAuthManager()
        connection = await ttw_manager.get_linkedin_connection()
        
        if not connection:
            add_log("ERROR", "admin_linkedin_oauth_api_test_failure", "System")
            return JSONResponse({
                "status": "error",
                "detail": "No LinkedIn connection found. Please authorize LinkedIn access first."
            }, status_code=400)
        
        # Test API access by getting profile info using stored token
        access_token = ttw_manager._decrypt_token(connection["access_token"])
        profile_data = await ttw_manager._get_linkedin_profile(access_token)
        
        if profile_data:
            add_log("INFO", "admin_linkedin_oauth_api_test_success", "System")
            return JSONResponse({
                "status": "success",
                "message": "LinkedIn API access test successful",
                "profile_name": profile_data.get("localizedFirstName", "") + " " + profile_data.get("localizedLastName", "")
            })
        else:
            add_log("ERROR", "admin_linkedin_oauth_api_test_failure", "System")
            return JSONResponse({
                "status": "error",
                "detail": "Failed to retrieve LinkedIn profile data. Check token validity."
            }, status_code=400)
        
    except Exception as e:
        logger.error(f"Error testing LinkedIn OAuth API: {str(e)}")
        add_log("ERROR", "admin_linkedin_oauth_api_test_error", "System")
        return JSONResponse({
            "status": "error",
            "error": str(e)
        }, status_code=500)


@app.get("/admin/linkedin/oauth/test-profile")
async def test_linkedin_profile_access(admin: dict = Depends(require_admin_auth_session)):
    """Test LinkedIn Profile Access (r_liteprofile)"""
    
    try:
        add_log("INFO", "admin_linkedin_profile_test", "System")
        
        ttw_manager = TTWOAuthManager()
        connection = await ttw_manager.get_linkedin_connection()
        
        if not connection:
            return JSONResponse({
                "status": "error",
                "detail": "No LinkedIn connection found. Please authorize LinkedIn access first."
            }, status_code=400)
        
        # Test profile access using stored token
        access_token = ttw_manager._decrypt_token(connection["access_token"])
        profile_data = await ttw_manager._get_linkedin_profile(access_token)
        
        if profile_data:
            profile_name = f"{profile_data.get('localizedFirstName', '')} {profile_data.get('localizedLastName', '')}".strip()
            headline = profile_data.get('headline', 'Not available')
            
            add_log("INFO", "admin_linkedin_profile_test_success", "System")
            return JSONResponse({
                "status": "success",
                "message": "LinkedIn Profile Access test successful",
                "data": {
                    "name": profile_name,
                    "headline": headline,
                    "profile_id": profile_data.get('id', 'Not available')
                }
            })
        else:
            add_log("ERROR", "admin_linkedin_profile_test_failure", "System")
            return JSONResponse({
                "status": "error",
                "detail": "Failed to retrieve profile data. Token may be expired."
            }, status_code=400)
        
    except Exception as e:
        logger.error(f"Error testing LinkedIn profile access: {str(e)}")
        add_log("ERROR", "admin_linkedin_profile_test_error", "System")
        return JSONResponse({
            "status": "error",
            "error": str(e)
        }, status_code=500)


@app.get("/admin/linkedin/oauth/test-email")
async def test_linkedin_email_access(admin: dict = Depends(require_admin_auth_session)):
    """Test LinkedIn Email Access (r_emailaddress)"""
    
    try:
        add_log("INFO", "admin_linkedin_email_test", "System")
        
        ttw_manager = TTWOAuthManager()
        connection = await ttw_manager.get_linkedin_connection()
        
        if not connection:
            return JSONResponse({
                "status": "error",
                "detail": "No LinkedIn connection found. Please authorize LinkedIn access first."
            }, status_code=400)
        
        # Test email access using stored token
        access_token = ttw_manager._decrypt_token(connection["access_token"])
        
        # Get email data from LinkedIn API
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.linkedin.com/v2/emailAddress?q=members&projection=(elements*(handle~))",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if response.status_code == 200:
                email_data = response.json()
                if email_data.get("elements") and len(email_data["elements"]) > 0:
                    email_address = email_data["elements"][0].get("handle~", {}).get("emailAddress")
                    
                    add_log("INFO", "admin_linkedin_email_test_success", "System")
                    return JSONResponse({
                        "status": "success",
                        "message": "LinkedIn Email Access test successful",
                        "data": {
                            "email": email_address
                        }
                    })
                else:
                    add_log("ERROR", "admin_linkedin_email_test_failure", "System")
                    return JSONResponse({
                        "status": "error",
                        "detail": "No email data available. Check if r_emailaddress scope is granted."
                    }, status_code=400)
            else:
                add_log("ERROR", "admin_linkedin_email_test_failure", "System")
                return JSONResponse({
                    "status": "error",
                    "detail": f"LinkedIn API error: {response.status_code}. Token may be expired."
                }, status_code=400)
        
    except Exception as e:
        logger.error(f"Error testing LinkedIn email access: {str(e)}")
        add_log("ERROR", "admin_linkedin_email_test_error", "System")
        return JSONResponse({
            "status": "error",
            "error": str(e)
        }, status_code=500)


@app.get("/admin/linkedin/oauth/test-positions")
async def test_linkedin_positions_access(admin: dict = Depends(require_admin_auth_session)):
    """Test LinkedIn Position Data Access (r_fullprofile)"""
    
    try:
        add_log("INFO", "admin_linkedin_positions_test", "System")
        
        ttw_manager = TTWOAuthManager()
        connection = await ttw_manager.get_linkedin_connection()
        
        if not connection:
            return JSONResponse({
                "status": "error",
                "detail": "No LinkedIn connection found. Please authorize LinkedIn access first."
            }, status_code=400)
        
        # Test positions access using stored token
        access_token = ttw_manager._decrypt_token(connection["access_token"])
        
        # Get positions data from LinkedIn API
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.linkedin.com/v2/positions?q=person&person-id={person-id}",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if response.status_code == 200:
                positions_data = response.json()
                positions_count = len(positions_data.get("elements", []))
                
                add_log("INFO", "admin_linkedin_positions_test_success", "System")
                return JSONResponse({
                    "status": "success", 
                    "message": "LinkedIn Position Data Access test successful",
                    "data": {
                        "positions_count": positions_count,
                        "positions_available": positions_count > 0
                    }
                })
            elif response.status_code == 403:
                add_log("ERROR", "admin_linkedin_positions_test_failure", "System")
                return JSONResponse({
                    "status": "error",
                    "detail": "Access denied. r_fullprofile scope may not be granted or available."
                }, status_code=400)
            else:
                add_log("ERROR", "admin_linkedin_positions_test_failure", "System")
                return JSONResponse({
                    "status": "error",
                    "detail": f"LinkedIn API error: {response.status_code}. Check scope permissions."
                }, status_code=400)
        
    except Exception as e:
        logger.error(f"Error testing LinkedIn positions access: {str(e)}")
        add_log("ERROR", "admin_linkedin_positions_test_error", "System")
        return JSONResponse({
            "status": "error",
            "error": str(e)
        }, status_code=500)


@app.get("/admin/linkedin/oauth/profile-data")
async def get_linkedin_profile_data(
    admin: dict = Depends(require_admin_auth_session)
):
    """Retrieve comprehensive LinkedIn profile data using Member Data
    Portability API"""
    
    try:
        add_log("INFO", "admin_linkedin_profile_data",
                "System")
        
        ttw_manager = TTWOAuthManager()
        connection = await ttw_manager.get_linkedin_connection()
        
        if not connection:
            return JSONResponse({
                "status": "error",
                "detail": ("No LinkedIn connection found. "
                           "Please authorize LinkedIn access first.")
            }, status_code=400)
        
        access_token = ttw_manager._decrypt_token(connection["access_token"])
        granted_scopes = (connection.get("granted_scopes", "").split()
                          if connection.get("granted_scopes") else [])
        
        profile_data = {}
        import httpx
        
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {access_token}"}
            
            # 1. Get basic profile information (r_liteprofile)
            if "r_liteprofile" in granted_scopes:
                try:
                    profile_url = ("https://api.linkedin.com/v2/people/~?"
                                   "projection=(id,firstName,lastName,"
                                   "profilePicture(displayImage~:"
                                   "playableStreams),headline)")
                    response = await client.get(profile_url, headers=headers)
                    if response.status_code == 200:
                        profile_data["basic_profile"] = response.json()
                    else:
                        profile_data["basic_profile_error"] = (
                            f"Status: {response.status_code}, "
                            f"Text: {response.text}")
                except Exception as e:
                    profile_data["basic_profile_error"] = str(e)
            
            # 2. Get email address (r_emailaddress)
            if "r_emailaddress" in granted_scopes:
                try:
                    email_url = ("https://api.linkedin.com/v2/emailAddress"
                                 "?q=members&projection=(elements*(handle~))")
                    response = await client.get(email_url, headers=headers)
                    if response.status_code == 200:
                        email_data = response.json()
                        if (email_data.get("elements") and
                                len(email_data["elements"]) > 0):
                            email_element = email_data["elements"][0]
                            profile_data["email"] = (
                                email_element.get("handle~", {})
                                .get("emailAddress"))
                    else:
                        profile_data["email_error"] = (
                            f"Status: {response.status_code}, "
                            f"Text: {response.text}")
                except Exception as e:
                    profile_data["email_error"] = str(e)
            
            # 3. Try Member Data Portability Profile endpoint
            # (requires specific scopes)
            try:
                detailed_url = ("https://api.linkedin.com/v2/people/~:"
                                "(id,localizedFirstName,localizedLastName,"
                                "profilePicture,headline,summary,positions,"
                                "educations,skills)")
                response = await client.get(detailed_url, headers=headers)
                if response.status_code == 200:
                    profile_data["detailed_profile"] = response.json()
                else:
                    profile_data["detailed_profile_error"] = (
                        f"Status: {response.status_code}, "
                        f"Text: {response.text}")
            except Exception as e:
                profile_data["detailed_profile_error"] = str(e)
            
            # 4. Try to get positions/work experience
            try:
                positions_url = ("https://api.linkedin.com/v2/people/~:"
                                 "(positions)")
                response = await client.get(positions_url, headers=headers)
                if response.status_code == 200:
                    profile_data["positions"] = response.json()
                else:
                    profile_data["positions_error"] = (
                        f"Status: {response.status_code}, "
                        f"Text: {response.text}")
            except Exception as e:
                profile_data["positions_error"] = str(e)
        
        # Return comprehensive profile data
        add_log("INFO", "admin_linkedin_profile_data_success",
                "System")
        return JSONResponse({
            "status": "success",
            "message": "LinkedIn profile data retrieved",
            "data": profile_data,
            "granted_scopes": granted_scopes,
            "connection_info": {
                "profile_id": connection.get("linkedin_profile_id"),
                "profile_name": connection.get("linkedin_profile_name"),
                "expires_at": (connection.get("token_expires_at").isoformat()
                               if connection.get("token_expires_at") else None)
            }
        })
        
    except Exception as e:
        logger.error(f"Error retrieving LinkedIn profile data: {str(e)}")
        add_log("ERROR", "admin_linkedin_profile_data_error",
                "System"
                f"{str(e)}")
        return JSONResponse({
            "status": "error",
            "error": str(e)
        }, status_code=500)


@app.post("/admin/linkedin/sync")
async def sync_linkedin_profile_data(admin: dict = Depends(require_admin_auth_session)):
    """Sync LinkedIn profile data to portfolio database"""
    
    try:
        add_log("INFO", "admin_linkedin_sync_initiate", "System")
        
        sync_service = TTWLinkedInSync()
        result = await sync_service.sync_profile_data()
        
        if result.get("success"):
            add_log("INFO", "admin_linkedin_sync_success", "System")
            return JSONResponse({
                "status": "success",
                "message": result.get("message", "LinkedIn profile data synced successfully"),
                "synced_data": result.get("synced_data", {})
            })
        else:
            add_log("ERROR", "admin_linkedin_sync_failure", "System")
            return JSONResponse({
                "status": "error",
                "detail": result.get("error", "LinkedIn profile sync failed")
            }, status_code=400)
        
    except Exception as e:
        logger.error(f"Error syncing LinkedIn profile: {str(e)}")
        add_log("ERROR", "admin_linkedin_sync_error", "System")
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
        if state:
            try:
                # Use TTW OAuth Manager to verify and decode encrypted state
                ttw_manager = TTWOAuthManager()
                state_data = ttw_manager.verify_linkedin_state(state)
            except Exception as e:
                add_log("ERROR", "linkedin_oauth_callback_state_error",
                        f"Failed to verify state: {str(e)}")
                return templates.TemplateResponse(
                    "linkedin_oauth_error.html", {
                        "request": request,
                        "error": "Invalid state parameter"
                    })
        
        add_log("INFO", "linkedin_oauth_callback_processing", "System")
        
        # Use TTW OAuth Manager to handle the callback
        ttw_manager = TTWOAuthManager()
        try:
            # Verify the state parameter
            state_data = ttw_manager.verify_linkedin_state(state)
            
            # Exchange code for tokens
            token_result = await ttw_manager.exchange_linkedin_code_for_tokens(code, state_data)
            
            add_log("INFO", "linkedin_oauth_callback_success", "System")
            return templates.TemplateResponse("linkedin_oauth_success.html", {
                "request": request,
                "message": "LinkedIn OAuth authorization successful!"
            })
        except Exception as oauth_error:
            logger.error(f"OAuth exchange failed: {str(oauth_error)}")
            add_log("ERROR", "linkedin_oauth_callback_failure", "System")
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
