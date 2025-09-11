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

# --- Third-Party Imports ---
from fastapi import (FastAPI, HTTPException, Request, Response)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import (HTMLResponse, JSONResponse)
from fastapi.security import HTTPBasic
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from strawberry.fastapi import GraphQLRouter

# --- Local Application Imports ---
from app.resolvers import schema
from app.routers import contact, projects, work, showcase, logs, sql
from app.routers.oauth import router as google_oauth_router
from app.routers.site_config import router as site_config_router
from app.routers.site_config_migration import (
    router as site_config_migration_router
)
from database import close_database, database, init_database
from log_capture import add_log
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
# The oauth object is now imported from oauth_client.py

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

    except Exception as e:
        logger.error(f"❌ Startup error: {str(e)}", exc_info=True)
        # Don't raise to allow app to start even with database issues
        logger.warning("⚠️ Starting app despite database issues")


@app.on_event("shutdown")
async def shutdown_event():
    await close_database()


# Template Data Extraction Endpoint
@app.post("/admin/extract-template-data")
async def extract_template_data():
    """Extract data from HTML templates and populate database"""
    try:
        from extract_template_data import extract_and_populate_data
        
        # Run the extraction in the background
        import asyncio
        await extract_and_populate_data()
        
        return JSONResponse({
            "success": True,
            "message": "Template data successfully extracted and populated in database"
        })
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        await add_log("ERROR", "template_extraction", f"Template extraction failed: {str(e)}", {"error": error_details})
        
        return JSONResponse({
            "success": False,
            "message": f"Failed to extract template data: {str(e)}"
        }, status_code=500)


# Include routers
app.include_router(contact.router, tags=["contact"])
app.include_router(projects.router, tags=["projects"])
app.include_router(google_oauth_router, tags=["oauth"])
app.include_router(work.router, tags=["work"])
app.include_router(showcase.router, tags=["showcase"])
app.include_router(logs.router, tags=["logs"])
app.include_router(sql.router, tags=["sql"])
app.include_router(site_config_router, tags=["config"])
app.include_router(site_config_migration_router, tags=["migration"])


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    from auth import get_user_info
    
    # Get user authentication data for navigation
    user_info = await get_user_info(request)
    user_authenticated = user_info is not None
    user_email = user_info.get('email') if user_info else None
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "title": "Daniel Blackburn - Software Developer & Solution Architect",
        "current_page": "home",
        "user_info": user_info,
        "user_authenticated": user_authenticated,
        "user_email": user_email
    })

