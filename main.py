# main.py - Lightweight FastAPI application with GraphQL and Google OAuth
# Restored to working state - ce98ca2 with full CRUD functionality

# --- Standard Library Imports ---
import logging
from logging.handlers import RotatingFileHandler
import os
import secrets
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

# --- Third-Party Imports ---
from authlib.integrations.starlette_client import OAuth
from fastapi import (Depends, FastAPI, HTTPException, Request, Response)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import (HTMLResponse, JSONResponse, RedirectResponse)
from fastapi.security import HTTPBasic
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from strawberry.fastapi import GraphQLRouter

# --- Local Application Imports ---
from app.resolvers import schema
from app.routers import contact, projects
from app.routers.oauth import router as google_oauth_router
from auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    is_authorized_user,
    require_admin_auth,
)
from cookie_auth import get_session_data
from database import close_database, database, init_database
from log_capture import add_log, log_with_context
from ttw_oauth_manager import TTWOAuthManager


def get_client_ip(request: Request) -> str:
    """Helper function to get client IP address from request."""
    if "x-forwarded-for" in request.headers:
        return request.headers["x-forwarded-for"].split(",")[0]
    return request.client.host if request.client else "unknown"


app = FastAPI(
    title="Blackburn Systems Portfolio",
    description=(
        "Portfolio website for Daniel Blackburn, showcasing projects, "
        "work experience, and technical skills."
    ),
    version="1.0.0"
)

# Session middleware for OAuth
# IMPORTANT: secret_key should be a long, random string in production
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET_KEY", "a-secure-secret-key")
)

# Initialize OAuth client
oauth = OAuth()

# Configure logging with dedicated portfoliosite.log file
# Create logs directory if it doesn't exist
os.makedirs('/var/log/portfoliosite', exist_ok=True)

# Configure main application logger
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - '
           '[%(filename)s:%(lineno)d] - %(funcName)s() - %(message)s',
    handlers=[
        # File handler for portfoliosite.log with rotation
        RotatingFileHandler(
            '/var/log/portfoliosite/portfoliosite.log',
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        ),
        # Console handler for development
        logging.StreamHandler()
    ]
)

# Get main logger
logger = logging.getLogger('portfoliosite')
logger.setLevel(logging.DEBUG)

# Set specific loggers to appropriate levels
logging.getLogger('uvicorn.access').setLevel(logging.INFO)
logging.getLogger('uvicorn.error').setLevel(logging.INFO)
logging.getLogger('databases').setLevel(logging.WARNING)

logger.info("=== Portfolio Application Logging Initialized ===")
logger.info("Log file: /var/log/portfoliosite/portfoliosite.log")
logger.info("Log level: %s", logger.level)
logger.info("Environment: %s", os.getenv('ENV', 'development'))


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

            # Add to database with correct parameter order: level, message,
            # module
            add_log(
                level=record.levelname,
                message=message,
                module=f"{module}_logging",
                function=record.funcName,
                line=record.lineno
            )

        except Exception as e:
            # Don't let logging errors break the application, but print for
            # debugging
            print(f"Database logging error: {e}")
            # Try to also log this error through standard logging
            try:
                import logging
                fallback_logger = logging.getLogger('database_handler_error')
                fallback_logger.error(f"Database handler failed: {e}")
            except Exception:
                pass


# Initialize TTW OAuth Manager
ttw_oauth_manager = TTWOAuthManager()


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
                    response_body = str(response.body)[:1000]
            except Exception:
                response_body = "Unable to capture response body"

            log_message = (
                f"{response.status_code} RESPONSE [{error_id}] "
                f"for {request.url}"
            )
            getattr(logger, logger_level)(log_message)

            # Log to database with enhanced details
            try:
                client_ip = get_client_ip(request)
                add_log(
                    level=log_level,
                    module="middleware",
                    message=(
                        f"[{error_id}] {response.status_code} response for "
                        f"{request.url}"
                    ),
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
                logger.error(
                    f"Failed to log {response.status_code} response to "
                    f"database: {log_error}"
                )
                logger.error(
                    "Database logging error traceback: "
                    f"{traceback.format_exc()}"
                )

        return response

    except Exception as e:
        # This should be caught by the global exception handler, but just in
        # case
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
            logger.error(
                f"Failed to log middleware error to database: {log_error}"
            )
            logger.error(
                "Database logging error traceback: "
                f"{traceback.format_exc()}"
            )

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
        detailed_message = (
            f"[{error_id}] {error_type}: {error_message}\n"
            f"URL: {request.url} | Method: {request.method}\n"
            f"Client IP: {client_ip}\n"
            f"Headers: {dict(request.headers)}"
        )

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
                "error_message": (
                    "An unexpected error occurred. "
                    "The technical team has been notified."
                ),
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
                "message": "An unexpected error occurred. Please try again.",
                "timestamp": error_time
            }
        )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with logging"""

    error_id = secrets.token_urlsafe(8)

    # Log HTTP exceptions
    logger.warning(
        f"HTTP EXCEPTION [{error_id}]: {exc.status_code} - {exc.detail} | "
        f"URL: {request.url}"
    )

    # Add to database log
    try:
        client_ip = get_client_ip(request)
        add_log(
            "WARNING",
            "http_exception_handler",
            (
                f"[{error_id}] {exc.status_code}: {exc.detail} | "
                f"URL: {request.url}"
            ),
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
password_status = (
    'SET' if ADMIN_PASSWORD and ADMIN_PASSWORD != 'admin' else 'DEFAULT'
)
logger.info(f"Admin password: {password_status}")
logger.info(f"Environment: {os.getenv('ENV', 'development')}")

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "your_secure_password_here")

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


# Add request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    method = request.method
    url = str(request.url)
    client_ip = request.client.host if request.client else "unknown"

    logger.info("=== Incoming Request ===")
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
                items.append(
                    f'<li><a href="{item.name}/">{item.name}/</a></li>'
                )
            else:
                size = item.stat().st_size
                size_str = f" ({size:,} bytes)"
                items.append(
                    f'<li><a href="{item.name}">{item.name}</a>{size_str}</li>'
                )

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
    """Initiate Google OAuth login via popup"""
    try:
        logger.info("=== OAuth Login Request Started ===")

        # Add log entry for login attempt
        log_with_context(
            "INFO",
            "auth",
            "User initiated Google OAuth login process",
            request
        )

        # Get fresh OAuth credentials from database before authorization
        try:
            ttw_manager = TTWOAuthManager()
            google_config = await ttw_manager.get_google_oauth_app_config()
            google_credentials = (
                await ttw_manager.get_google_oauth_credentials()
            )

            if not google_config or not google_credentials:
                return JSONResponse({
                    "status": "error",
                    "error": "Google OAuth is not configured.",
                    "redirect": "/admin/google/oauth"
                }, status_code=503)

            # Re-register OAuth client with fresh credentials
            oauth.register(
                name='google',
                client_id=google_config['client_id'],
                client_secret=google_credentials['client_secret'],
                redirect_uri=google_config['redirect_uri'],
                server_metadata_url=(
                    'https://accounts.google.com/.well-known/'
                    'openid-configuration'
                ),
                client_kwargs={'scope': 'openid email profile'}
            )

            redirect_uri = google_config['redirect_uri']
            logger.info(
                f"Using fresh OAuth config - Client ID: "
                f"{google_config['client_id'][:10]}..., "
                f"Redirect URI: {redirect_uri}"
            )

        except Exception as config_error:
            logger.error(f"Failed to get fresh OAuth config: {config_error}")
            return JSONResponse({
                "status": "error",
                "error": "Failed to load OAuth configuration from database."
            }, status_code=503)

        # Generate and store state parameter for CSRF protection
        import secrets
        state = secrets.token_urlsafe(32)
        request.session['oauth_state'] = state

        # Define explicit scopes for login (basic scopes only)
        scopes = ['openid', 'email', 'profile']

        # Use the OAuth client to get auth URL
        google = oauth.google
        try:
            result = await google.authorize_redirect(
                request,
                redirect_uri,
                scope=' '.join(scopes),
                state=state,
                access_type='offline',  # Request refresh token
                prompt='select_account'  # Allow account selection
            )

            # Extract the redirect URL from the response
            if hasattr(result, 'headers') and 'location' in result.headers:
                auth_url = result.headers['location']
            else:
                # Fallback - construct URL manually
                auth_url = str(result)

            logger.info(
                "OAuth auth URL created successfully with state: "
                f"{state[:8]}..."
            )

            return JSONResponse({
                "status": "success",
                "auth_url": auth_url,
                "requested_scopes": scopes
            })

        except Exception as redirect_error:
            logger.error(f"OAuth redirect error: {str(redirect_error)}")
            return JSONResponse({
                "status": "error",
                "error": f"OAuth configuration error: {str(redirect_error)}"
            }, status_code=500)

    except Exception as e:
        logger.error(f"OAuth login error: {str(e)}")
        logger.exception("Full traceback:")
        return JSONResponse({
            "status": "error",
            "error": f"Authentication error: {str(e)}"
        }, status_code=500)


@app.get("/auth/login/redirect")
async def auth_login_redirect(request: Request):
    """Legacy redirect-based login for backward compatibility"""
    try:
        # Get the auth URL from the main endpoint
        auth_response = await auth_login(request)

        if auth_response.status_code == 200:
            import json
            auth_data = json.loads(auth_response.body)
            if auth_data.get("status") == "success":
                # Redirect to the auth URL
                return RedirectResponse(url=auth_data["auth_url"])

        # If there was an error, show error page
        return HTMLResponse(
            content="""
            <html><body>
            <h1>OAuth Login Failed</h1>
            <p>Unable to initiate OAuth login. Please try again.</p>
            <p><a href="/">Return to main site</a></p>
            </body></html>
            """,
            status_code=500
        )

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
                        body {
                            font-family: Arial, sans-serif;
                            text-align: center;
                            padding: 50px;
                        }
                        .warning { color: #ffc107; }
                    </style>
                </head>
                <body>
                <h2 class="warning">⚠️ Authorization Cancelled</h2>
                <p>You cancelled the Google authorization process.</p>
                <p>To use admin features, you'll need to grant the required
                   permissions.</p>
                <p>
                    <a href="/admin/google/oauth">Try again</a> |
                    <a href="/">Return to main site</a>
                </p>
                <script>
                    // If this is a popup, close it after a delay
                    if (window.opener) {
                        setTimeout(function() {
                            try {
                                window.opener.postMessage(
                                    { type: 'OAUTH_CANCELLED' },
                                    window.location.origin
                                );
                            } catch (e) {
                                console.log('Could not notify parent window:',
                                              e);
                            }
                            window.close();
                        }, 3000);
                    }
                </script>
                </body>
                </html>
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
                <p>
                    <a href="/admin/google/oauth">Try again</a> |
                    <a href="/">Return to main site</a>
                </p>
                </body></html>
                """,
                status_code=400
            )

    # Get fresh OAuth credentials from database for callback
    try:
        ttw_manager = TTWOAuthManager()
        google_config = await ttw_manager.get_google_oauth_app_config()
        google_credentials = await ttw_manager.get_google_oauth_credentials()

        if google_config and google_credentials:
            # Re-register OAuth client with fresh credentials for callback
            oauth.register(
                name='google',
                client_id=google_config['client_id'],
                client_secret=google_credentials['client_secret'],
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
        logger.error(
            f"Failed to refresh OAuth config in callback: {config_error}"
        )

    try:
        # Debug state validation
        callback_state = request.query_params.get('state')
        session_state = request.session.get('oauth_state')
        logger.info(
            "Callback state: "
            f"{callback_state[:8] if callback_state else 'NONE'}..."
        )
        logger.info(
            "Session state: "
            f"{session_state[:8] if session_state else 'NONE'}..."
        )
        logger.info(f"State match: {callback_state == session_state}")

        # Validate CSRF state parameter
        if not callback_state or not session_state or \
           callback_state != session_state:
            logger.error(
                "CSRF validation failed - callback: "
                f"{callback_state[:8] if callback_state else 'NONE'}, "
                "session: "
                f"{session_state[:8] if session_state else 'NONE'}"
            )
            return HTMLResponse(
                content="""
                <html><body>
                <h1>Security Error</h1>
                <p>CSRF validation failed. This could be due to:</p>
                <ul>
                    <li>Session timeout</li>
                    <li>Browser security restrictions</li>
                    <li>Invalid request state</li>
                </ul>
                <p>
                    <a href="/auth/login">Try logging in again</a> |
                    <a href="/">Return to main site</a>
                </p>
                </body></html>
                """,
                status_code=400
            )

        # Clear the state from session after validation
        request.session.pop('oauth_state', None)

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

        logger.info("About to exchange code for token...")
        google = oauth.google
        token = await google.authorize_access_token(request)
        logger.info(f"Token received: {bool(token)}")

        user_info = token.get('userinfo')

        if not user_info:
            # Fallback to get user info from Google
            resp = await google.get(
                'https://www.googleapis.com/oauth2/v1/userinfo',
                token=token
            )
            user_info = resp.json()

        email = user_info.get('email')
        if not email:
            return HTMLResponse(
                content="""
                <html><body>
                <h1>Authentication Error</h1>
                <p>No email found in Google account.</p>
                <p>
                    <a href="/auth/login">Try again</a> |
                    <a href="/">Return to main site</a>
                </p>
                </body></html>
                """,
                status_code=400
            )

        if not is_authorized_user(email):
            add_log("WARNING", "auth",
                    f"Unauthorized login attempt by {email}")
            return HTMLResponse(
                content=f"""
                <html><head><title>Unauthorized</title></head><body>
                <h2>Unauthorized</h2>
                <p>Your email ({email}) is not authorized to access this
                   admin panel.</p>
                <p><a href="/auth/login">Try again</a></p>
                </body></html>
                """,
                status_code=403
            )

        access_token = create_access_token(data={"sub": email})
        log_with_context(
            "INFO", "auth", f"Successful login by {email} - JWT created",
            request
        )

        # The response will be an HTML page that communicates with the parent
        # window
        response = HTMLResponse(content="""
            <html><head><title>Authenticated</title></head><body>
                <script>
                    try {
                        window.opener.postMessage(
                            { type: 'OAUTH_SUCCESS' },
                            window.location.origin
                        );
                    } catch (e) {
                        console.error('Could not notify parent window.', e);
                    }
                    window.close();
                </script>
                <p>Authentication successful. You can close this window.</p>
            </body></html>
        """)
        response.set_cookie(
            key="access_token",
            value=f"Bearer {access_token}",
            httponly=True,
            secure=True,
            samesite="Lax",
            max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        return response

    except Exception as e:
        logger.error(f"Error during Google OAuth callback: {e}", exc_info=True)
        return HTMLResponse(
            content="""
            <html><head><title>Error</title></head><body>
            <h2>Authentication Error</h2>
            <p>An unexpected error occurred during authentication.</p>
            <p>
                <a href="/auth/login">Try again</a> |
                <a href="/">Return to main site</a>
            </p>
            </body></html>
            """,
            status_code=500
        )


@app.post("/auth/logout")
async def logout(request: Request, response: HTMLResponse):
    """Log out the user by clearing session state"""
    try:
        logger.info("=== Session Logout Request ===")

        # Get user info from session before clearing
        user_email = "unknown"
        if hasattr(request, 'session') and 'user' in request.session:
            user_session = request.session.get('user', {})
            user_email = user_session.get('email', 'unknown')

        # Add log entry for logout
        log_with_context(
            "INFO", "auth", f"User logged out: {user_email}", request
        )

        # Clear all session data
        request.session.clear()

        logger.info("Successfully cleared session data")
        return RedirectResponse(url="/", status_code=303)
    except Exception as e:
        logger.error(f"Logout error: {str(e)}", exc_info=True)
        return RedirectResponse(url="/", status_code=303)


@app.get("/admin/status", response_class=JSONResponse)
async def get_admin_status(request: Request):
    """Endpoint to check authentication status from the frontend."""
    user_info = get_session_data(request)
    is_authenticated = user_info is not None
    user_email = user_info.get("email") if user_info else None

    return {
        "is_authenticated": is_authenticated,
        "user_email": user_email,
        "is_admin": is_authorized_user(user_email) if user_email else False
    }


@app.get("/admin/google/oauth", response_class=HTMLResponse)
async def google_oauth_admin(request: Request):
    """Google OAuth administration interface."""
    add_log(
        "INFO",
        "admin_google_oauth_page_access",
        "Google OAuth admin page accessed (no auth)"
    )

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
async def google_oauth_status(
    request: Request, admin: dict = Depends(require_admin_auth)
):
    """Get Google OAuth configuration and connection status"""

    try:
        add_log("DEBUG", "oauth_status_check", "System")

        # Check if Google OAuth is configured in database
        ttw_manager = TTWOAuthManager()
        google_configured = await ttw_manager.is_google_oauth_app_configured()

        add_log(
            "DEBUG",
            "oauth_configured_result",
            f"Google configured: {google_configured}"
        )

        config = None
        credentials = None
        if google_configured:
            config = await ttw_manager.get_google_oauth_app_config()
            credentials = await ttw_manager.get_google_oauth_credentials()
            add_log(
                "DEBUG", "oauth_config_loaded",
                (f"Config: {config is not None}, "
                 f"Credentials: {credentials is not None}")
            )
            add_log("DEBUG", "oauth_config_content", f"Config: {config}")
            add_log(
                "DEBUG",
                "oauth_credentials_content",
                f"Credentials: {credentials}"
            )

        # Check current session for Google auth
        google_connected = "user" in request.session and hasattr(
            request, 'session'
        )

        # Build response with detailed logging
        client_secret = credentials.get(
            "client_secret", ""
        ) if credentials else ""
        add_log(
            "DEBUG", "oauth_client_secret_check",
            f"Secret: {'[PRESENT]' if client_secret else '[EMPTY]'}"
        )

        # Log the exact values being returned
        client_id = config.get("client_id", "") if config else ""
        redirect_uri = config.get("redirect_uri", "") if config else ""

        add_log(
            "DEBUG", "oauth_status_response_values",
            (f"ID: '{client_id}', Secret: "
             f"'{'[PRESENT]' if client_secret else '[EMPTY]'}', "
             f"URI: '{redirect_uri}'")
        )

        response_data = {
            "configured": google_configured,
            "connected": google_connected,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "account_email": (request.session.get("user", {})
                              .get("email") if google_connected else None),
            "last_sync": (request.session.get("user", {})
                          .get("login_time") if google_connected else None),
            "token_expiry": (request.session.get("user", {})
                             .get("expires_at") if google_connected else None)
        }

        add_log(
            "DEBUG",
            "oauth_status_full_response",
            f"Full response: {response_data}"
        )

        return JSONResponse(response_data)

    except Exception as e:
        add_log(
            "ERROR",
            "oauth_status_error",
            f"Error getting Google OAuth status: {str(e)}"
        )
        logger.error(f"Error getting Google OAuth status: {str(e)}")
        return JSONResponse({
            "status": "error",
            "error": str(e)
        }, status_code=500)


@app.post("/admin/google/oauth/config")
async def save_google_oauth_config(
    request: Request,
    config: dict,
    admin: dict = Depends(require_admin_auth)
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
        logger.error(
            f"Error saving Google OAuth config: {str(e)}\n"
            f"Traceback: {full_traceback}"
        )
        log_with_context(
            "ERROR", "admin_google_oauth_config_error",
            (f"Error saving Google OAuth config: {str(e)}\n"
             f"Traceback: {full_traceback}"),
            request
        )
        return JSONResponse({
            "status": "error",
            "error": str(e),
            "traceback": full_traceback
        }, status_code=500)


@app.delete("/admin/google/oauth/config")
async def clear_google_oauth_config(
    admin: dict = Depends(require_admin_auth)
):
    """Clear Google OAuth configuration"""

    try:
        add_log("INFO", "Clearing Google OAuth configuration", "main")

        ttw_manager = TTWOAuthManager()
        result = await ttw_manager.remove_google_oauth_app()

        if result:
            add_log("INFO", "Google OAuth config cleared successfully", "main")
            return JSONResponse({
                "status": "success",
                "message": "Google OAuth config cleared successfully"
            })
        else:
            return JSONResponse({
                "status": "error",
                "detail": "Failed to clear Google OAuth configuration"
            }, status_code=500)

    except Exception as e:
        logger.error(f"Error clearing Google OAuth config: {str(e)}")
        add_log(
            "ERROR",
            f"Error clearing Google OAuth config: {str(e)}",
            "main"
        )
        return JSONResponse({
            "status": "error",
            "error": str(e)
        }, status_code=500)


@app.get("/admin/google/oauth/authorize")
async def initiate_google_oauth(
    request: Request, admin: dict = Depends(require_admin_auth)
):
    """Initiate Google OAuth flow with explicit scope permissions"""

    try:
        add_log("INFO", "Initiating Google OAuth authorization", "main")

        # Get fresh OAuth configuration from database
        try:
            ttw_manager = TTWOAuthManager()
            google_config = await ttw_manager.get_google_oauth_app_config()

            if not google_config:
                logger.error("No Google OAuth config found in database")
                raise HTTPException(
                    status_code=503,
                    detail="Google OAuth is not configured"
                )

            redirect_uri = google_config['redirect_uri']
            logger.info(
                "Using OAuth redirect URI from database: "
                f"{redirect_uri}"
            )

        except Exception as config_error:
            logger.error(
                "Failed to get OAuth config from database: "
                f"{config_error}"
            )
            raise HTTPException(
                status_code=500,
                detail="Failed to retrieve OAuth configuration"
            )

        # Generate a new state parameter for CSRF protection
        import secrets
        state = secrets.token_urlsafe(32)
        request.session['oauth_state'] = state

        # Define explicit scopes that we're requesting
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
            prompt='consent'        # Force consent screen
        )

        # Extract the redirect URL from the response
        has_headers = hasattr(auth_result, 'headers')
        if has_headers and 'location' in auth_result.headers:
            auth_url = auth_result.headers['location']
        else:
            # Fallback - construct URL manually
            auth_url = str(auth_result)

        return JSONResponse({
            "status": "success",
            "auth_url": auth_url,
            "requested_scopes": scopes,
            "scope_descriptions": {
                "openid": "Basic identity verification",
                "email": "Email address access",
                "profile": "Profile information access"
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
async def revoke_google_oauth(
    request: Request, admin: dict = Depends(require_admin_auth)
):
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


def get_auth_status() -> Dict[str, Any]:
    """Helper to get auth status, to be replaced or removed."""
    # This is a placeholder. In a real app, you'd check a session
    # or token.
    return {"is_authenticated": False, "user_email": None}


# Include routers
app.include_router(contact.router, tags=["contact"])
app.include_router(projects.router, tags=["projects"])
