# main.py - Lightweight FastAPI application with GraphQL
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, Response, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from strawberry.fastapi import GraphQLRouter
from pydantic import BaseModel
from typing import Optional, List
import uvicorn
import json
import os
from pathlib import Path
import sqlite3
import asyncio

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
templates = Jinja2Templates(directory="templates")

# Database initialization
@app.on_event("startup")
async def startup_event():
    if DATABASE_AVAILABLE:
        await init_database()
    else:
        print("Running without database connection")


@app.on_event("shutdown")
async def shutdown_event():
    if DATABASE_AVAILABLE:
        await close_database()

# Routes for serving the portfolio website
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Serve the main portfolio page"""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "title": "Daniel Blackburn - Building innovative solutions",
        "current_page": "home"
    })

@app.get("/contact/", response_class=HTMLResponse)
async def contact(request: Request):
    """Serve the contact page"""
    return templates.TemplateResponse("contact.html", {
        "request": request,
        "title": "Contact - Daniel Blackburn",
        "current_page": "contact"
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
        "title": "Work - daniel blackburn",
        "current_page": "work"
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
async def work_admin_page(request: Request):
    return templates.TemplateResponse("workadmin.html", {
        "request": request,
        "current_page": "workadmin"
    })


@app.get("/workadmin/bulk", response_class=HTMLResponse)
async def work_admin_bulk_page(request: Request):
    """New bulk editor interface for work items"""
    return templates.TemplateResponse("workadmin_bulk.html", {
        "request": request,
        "current_page": "workadmin_bulk"
    })


# --- Projects Admin Page ---
@app.get("/projectsadmin", response_class=HTMLResponse)
async def projects_admin_page(request: Request):
    return templates.TemplateResponse("projectsadmin.html", {
        "request": request,
        "current_page": "projectsadmin"
    })


@app.get("/projectsadmin/bulk", response_class=HTMLResponse)
async def projects_admin_bulk_page(request: Request):
    """New bulk editor interface for projects"""
    return templates.TemplateResponse("projectsadmin_bulk.html", {
        "request": request,
        "current_page": "projectsadmin_bulk"
    })


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
async def create_workitem(item: WorkItem):
    query = """
        INSERT INTO work_experience (portfolio_id, company, position, location, start_date, end_date, description, is_current, company_url, sort_order)
        VALUES (:portfolio_id, :company, :position, :location, :start_date, :end_date, :description, :is_current, :company_url, :sort_order)
        RETURNING *
    """
    row = await database.fetch_one(query, item.dict(exclude_unset=True))
    return WorkItem(**dict(row))

# Update a work item
@app.put("/workitems/{id}", response_model=WorkItem)
async def update_workitem(id: str, item: WorkItem):
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
async def delete_workitem(id: str):
    query = "DELETE FROM work_experience WHERE id=:id"
    result = await database.execute(query, {"id": id})
    return {"success": True}


# --- Bulk Operations for Work Items ---

@app.post("/workitems/bulk", response_model=BulkWorkItemsResponse)
async def bulk_create_update_workitems(request: BulkWorkItemsRequest):
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
async def bulk_delete_workitems(request: BulkDeleteRequest):
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
async def create_project(project: Project):
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
async def update_project(id: str, project: Project):
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
async def delete_project(id: str):
    query = "DELETE FROM projects WHERE id=:id"
    result = await database.execute(query, {"id": id})
    return {"deleted": True, "id": id}


# Bulk create/update projects
@app.post("/projects/bulk", response_model=BulkProjectsResponse)
async def bulk_create_update_projects(request: BulkProjectsRequest):
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
async def bulk_delete_projects(request: BulkDeleteRequest):
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
