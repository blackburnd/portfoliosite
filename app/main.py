from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.templating import Jinja2Templates
from strawberry.fastapi import GraphQLRouter
from pydantic import BaseModel
from typing import Optional, List
import app.resolvers as resolvers
import databases
import os

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Centralized database connection function
def get_database_connection():
    """Get a database connection using environment variables"""
    database_url = os.getenv("_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("No database URL found in environment variables")
    return databases.Database(database_url)

# Database connection
db = get_database_connection()

# Pydantic model for work item
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

# GraphQL endpoint
graphql_app = GraphQLRouter(resolvers.schema)
app.include_router(graphql_app, prefix="/graphql")

# Database connection events
@app.on_event("startup")
async def startup():
    await db.connect()

@app.on_event("shutdown")
async def shutdown():
    await db.disconnect()

@app.get("/profile")
def get_profile():
    return {"name": "Your Name", "bio": "Short bio here."}

@app.get("/portfolio")
def get_portfolio():
    return {"projects": [
        {"title": "Project 1", "description": "Description of project 1."},
        {"title": "Project 2", "description": "Description of project 2."}
    ]}

# /work page populated via GraphQL
@app.get("/work", response_class=HTMLResponse)
async def work_page():
    # Query GraphQL endpoint for work experience
    import httpx
    query = """
    query {
        workExperience {
            company
            position
            startDate
            endDate
            description
        }
    }
    """
    async with httpx.AsyncClient() as client:
        resp = await client.post("http://localhost:8000/graphql", json={"query": query})
        data = resp.json()
    work_items = data.get("data", {}).get("workExperience", [])
    html = "<h1>Work Experience</h1><ul>"
    for item in work_items:
        html += f"<li><strong>{item['company']}</strong> - {item['position']} ({item['startDate']} - {item.get('endDate','Present')})<br>{item['description']}</li>"
    html += "</ul>"
    return html

# /schema page returns DB schema info
@app.get("/schema", response_class=JSONResponse)
async def schema_page():
    # Connect to DB
    db = get_database_connection()
    await db.connect()
    # Get tables
    tables = await db.fetch_all("""
        SELECT table_name FROM information_schema.tables WHERE table_schema='public'
    """)
    result = {}
    for t in tables:
        table = t[0] if isinstance(t, tuple) else t['table_name']
        # Get columns
        columns = await db.fetch_all(f"""
            SELECT column_name, data_type FROM information_schema.columns WHERE table_name='{table}'
        """)
        # Get count
        count = await db.fetch_val(f"SELECT COUNT(*) FROM {table}")
        result[table] = {
            "columns": [{"name": c[0] if isinstance(c, tuple) else c['column_name'], "type": c[1] if isinstance(c, tuple) else c['data_type']} for c in columns],
            "count": count
        }
    await db.disconnect()
    return result

# --- Resume Download Route ---
@app.get("/resume/download", response_class=FileResponse)
async def download_resume():
    resume_path = "assets/files/danielblackburn.pdf"
    return FileResponse(resume_path, media_type="application/pdf", filename="danielblackburn_resume.pdf")

# --- Resume View Route ---
@app.get("/resume", response_class=FileResponse)
async def view_resume():
    resume_path = "assets/files/danielblackburn.pdf"
    return FileResponse(resume_path, media_type="application/pdf")

# --- Work Admin Page ---
@app.get("/workadmin", response_class=HTMLResponse)
async def work_admin_page(request: Request):
    return templates.TemplateResponse("workadmin.html", {"request": request})

# --- CRUD Endpoints for Work Items ---

# List all work items
@app.get("/workitems", response_model=List[WorkItem])
async def list_workitems():
    query = "SELECT * FROM work_experience ORDER BY sort_order, start_date DESC"
    rows = await db.fetch_all(query)
    return [WorkItem(**dict(row)) for row in rows]

# Create a new work item
@app.post("/workitems", response_model=WorkItem)
async def create_workitem(item: WorkItem):
    query = """
        INSERT INTO work_experience (portfolio_id, company, position, location, start_date, end_date, description, is_current, company_url, sort_order)
        VALUES (:portfolio_id, :company, :position, :location, :start_date, :end_date, :description, :is_current, :company_url, :sort_order)
        RETURNING *
    """
    row = await db.fetch_one(query, item.dict(exclude_unset=True))
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
    row = await db.fetch_one(query, values)
    if not row:
        raise HTTPException(status_code=404, detail="Work item not found")
    return WorkItem(**dict(row))

# Delete a work item
@app.delete("/workitems/{id}")
async def delete_workitem(id: str):
    query = "DELETE FROM work_experience WHERE id=:id"
    result = await db.execute(query, {"id": id})
    return {"success": True}
