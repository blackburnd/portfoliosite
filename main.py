# main.py - Lightweight FastAPI application with GraphQL
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, Response, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from strawberry.fastapi import GraphQLRouter
import uvicorn
import os
from pathlib import Path

from app.resolvers import schema
from database import init_database, close_database, database


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_database()
    yield
    # Shutdown
    await close_database()


# Initialize FastAPI app
app = FastAPI(
    title="Portfolio API",
    description="Lightweight GraphQL API for Daniel's Portfolio Website",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GraphQL router
graphql_app = GraphQLRouter(schema)
app.include_router(graphql_app, prefix="/graphql")

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
app.mount("/templates", StaticFiles(directory="templates"), name="templates")
templates = Jinja2Templates(directory="templates")

# Routes for serving the portfolio website
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Serve the main portfolio page"""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "title": "Daniel Blackburn - Building innovative solutions"
    })

@app.get("/contact/", response_class=HTMLResponse)
async def contact(request: Request):
    """Serve the contact page"""
    return templates.TemplateResponse("contact.html", {
        "request": request,
        "title": "Contact - Daniel Blackburn"
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
    return templates.TemplateResponse("work.html", {
        "request": request,
        "title": "Work - daniel blackburn"
    })

@app.get("/resume/")
async def resume():
    """Redirect to local resume PDF file"""
    return RedirectResponse(
        url="/assets/files/danielblackburn.pdf",  # Updated to match your actual filename
        status_code=302
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
