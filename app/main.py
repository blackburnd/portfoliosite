import sys
import os
from typing import Optional, List

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from strawberry.fastapi import GraphQLRouter
from starlette.middleware.sessions import SessionMiddleware

# Add parent directory to path for local imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app.resolvers as resolvers
from app.routers import admin, contact, logs, oauth, projects, showcase, sql, work
from database import database, init_database, close_database


app = FastAPI()

# Add session middleware, required for OAuth user session
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SECRET_KEY", "a_secret_key"))

templates = Jinja2Templates(directory="templates")


@app.on_event("startup")
async def startup():
    """Initialize database connection on startup."""
    await init_database()


@app.on_event("shutdown")
async def shutdown():
    """Close database connection on shutdown."""
    await close_database()


# --- Pydantic Models ---
class WorkItem(BaseModel):
    id: Optional[str]
    portfolio_id: str
    company: str
    position: str
    location: Optional[str]
    start_date: Optional[str]
    end_date: Optional[str]
    description: Optional[str]
    is_current: Optional[bool] = False
    company_url: Optional[str]
    sort_order: Optional[int] = 0


# --- Routers ---
# Include all modular routers
app.include_router(admin.router)
app.include_router(contact.router)
app.include_router(logs.router)
app.include_router(oauth.router)
app.include_router(projects.router)
app.include_router(showcase.router)
app.include_router(sql.router)
app.include_router(work.router)

# GraphQL endpoint
graphql_app = GraphQLRouter(resolvers.schema)
app.include_router(graphql_app, prefix="/graphql")


# --- Home Route ---
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Serve the home page with authentication status"""
    user_authenticated = False
    user_email = None
    user_info = None
    
    try:
        # Import auth functions locally to avoid circular imports
        from auth import verify_token, is_authorized_user
        
        token = request.cookies.get("access_token")
        if token:
            payload = verify_token(token)
            email = payload.get("sub")
            if email and is_authorized_user(email):
                user_authenticated = True
                user_email = email
                user_info = {
                    "email": email,
                    "name": payload.get("name", email.split("@")[0])
                }
    except Exception:
        pass  # Continue with unauthenticated state
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "current_page": "home",
        "user_authenticated": user_authenticated,
        "user_email": user_email,
        "user_info": user_info
    })


# --- Legacy Routes (to be phased out) ---

@app.get("/profile")
def get_profile():
    """Placeholder for a user profile endpoint."""
    return {"name": "Your Name", "bio": "Short bio here."}


@app.get("/portfolio")
def get_portfolio():
    """Placeholder for a portfolio endpoint."""
    return {
        "projects": [
            {"title": "Project 1", "description": "Description of project 1."},
            {"title": "Project 2", "description": "Description of project 2."},
        ]
    }


@app.get("/schema", response_class=JSONResponse)
async def schema_page():
    """Endpoint to display database schema information."""
    tables = await database.fetch_all(
        "SELECT table_name FROM information_schema.tables WHERE table_schema='public'"
    )
    result = {}
    for t in tables:
        table = t[0] if isinstance(t, tuple) else t["table_name"]
        columns = await database.fetch_all(
            f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name='{table}'"
        )
        count = await database.fetch_val(f"SELECT COUNT(*) FROM {table}")
        result[table] = {
            "columns": [
                {
                    "name": c[0] if isinstance(c, tuple) else c["column_name"],
                    "type": c[1] if isinstance(c, tuple) else c["data_type"],
                }
                for c in columns
            ],
            "count": count,
        }
    return result


# --- CRUD Endpoints for Work Items (consider moving to work router) ---

@app.get("/workitems", response_model=List[WorkItem])
async def list_workitems():
    """List all work items for the portfolio."""
    from database import PORTFOLIO_ID
    query = "SELECT * FROM work_experience WHERE portfolio_id = :portfolio_id ORDER BY sort_order, start_date DESC"
    rows = await database.fetch_all(query, {"portfolio_id": PORTFOLIO_ID})
    return [WorkItem(**dict(row)) for row in rows]


@app.post("/workitems", response_model=WorkItem)
async def create_workitem(item: WorkItem):
    """Create a new work item."""
    query = """
        INSERT INTO work_experience (portfolio_id, company, position, location, start_date, end_date, description, is_current, company_url, sort_order)
        VALUES (:portfolio_id, :company, :position, :location, :start_date, :end_date, :description, :is_current, :company_url, :sort_order)
        RETURNING *
    """
    # Use .dict() and exclude unset to handle optional fields correctly
    values = item.dict(exclude_unset=True)
    # Ensure portfolio_id is set if not provided in the request body
    if 'portfolio_id' not in values:
        from database import PORTFOLIO_ID
        values['portfolio_id'] = PORTFOLIO_ID

    row = await database.fetch_one(query, values)
    return WorkItem(**dict(row))


@app.put("/workitems/{item_id}", response_model=WorkItem)
async def update_workitem(item_id: str, item: WorkItem):
    """Update an existing work item."""
    query = """
        UPDATE work_experience SET
            company=:company, position=:position, location=:location, start_date=:start_date, end_date=:end_date,
            description=:description, is_current=:is_current, company_url=:company_url, sort_order=:sort_order, updated_at=NOW()
        WHERE id=:id RETURNING *
    """
    values = item.dict(exclude_unset=True)
    values["id"] = item_id
    row = await database.fetch_one(query, values)
    if not row:
        raise HTTPException(status_code=404, detail="Work item not found")
    return WorkItem(**dict(row))


@app.delete("/workitems/{item_id}")
async def delete_workitem(item_id: str):
    """Delete a work item."""
    query = "DELETE FROM work_experience WHERE id=:id"
    await database.execute(query, {"id": item_id})
    return {"success": True}
