from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional, List
import json

from auth import require_admin_auth
from database import database, PORTFOLIO_ID, get_portfolio_id

router = APIRouter()
templates = Jinja2Templates(directory="templates")


class Project(BaseModel):
    id: Optional[str] = None
    portfolio_id: Optional[str] = None
    title: str
    description: str
    url: Optional[str] = None
    image_url: Optional[str] = None
    technologies: Optional[List[str]] = []
    sort_order: Optional[int] = 0


@router.get("/projects/", response_class=HTMLResponse)
async def projects(request: Request):
    """Serve the projects page"""
    return templates.TemplateResponse("projects.html", {
        "request": request,
        "title": "Projects - Daniel Blackburn",
        "current_page": "projects"
    })


@router.get("/projectsadmin", response_class=HTMLResponse)
async def projects_admin_page(
    request: Request,
    admin: dict = Depends(require_admin_auth)
):
    return templates.TemplateResponse("projectsadmin.html", {
        "request": request,
        "current_page": "projectsadmin",
        "user_info": admin,
        "user_authenticated": True,
        "user_email": admin.get("email", ""),
        "portfolio_id": get_portfolio_id()
    })


@router.get("/projects", response_model=List[Project])
async def list_projects():
    try:
        check_table = "SELECT to_regclass('projects')"
        table_exists = await database.fetch_val(check_table)
        
        if not table_exists:
            return []
            
        portfolio_id = PORTFOLIO_ID
        query = """
            SELECT * FROM projects 
            WHERE portfolio_id = :portfolio_id 
            ORDER BY sort_order, title
        """
        rows = await database.fetch_all(query, {"portfolio_id": portfolio_id})
        
        projects = []
        for row in rows:
            row_dict = dict(row)
            technologies = row_dict.get("technologies", [])
            if isinstance(technologies, str):
                try:
                    technologies = json.loads(technologies)
                except (json.JSONDecodeError, TypeError):
                    technologies = []
            
            project = Project(
                id=str(row_dict["id"]),
                portfolio_id=row_dict.get("portfolio_id", get_portfolio_id()),
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


@router.get("/projects/{id}", response_model=Project)
async def get_project(id: str, admin: dict = Depends(require_admin_auth)):
    portfolio_id = PORTFOLIO_ID
    query = "SELECT * FROM projects WHERE id = :id AND portfolio_id = :portfolio_id"
    row = await database.fetch_one(query, {"id": id, "portfolio_id": portfolio_id})
    
    if not row:
        raise HTTPException(status_code=404, detail="Project not found")
    
    row_dict = dict(row)
    technologies = row_dict.get("technologies", [])
    if isinstance(technologies, str):
        try:
            technologies = json.loads(technologies)
        except (json.JSONDecodeError, TypeError):
            technologies = []
    
    return Project(
        id=str(row_dict["id"]),
        portfolio_id=row_dict.get("portfolio_id", get_portfolio_id()),
        title=row_dict.get("title", ""),
        description=row_dict.get("description", ""),
        url=row_dict.get("url"),
        image_url=row_dict.get("image_url"),
        technologies=technologies,
        sort_order=row_dict.get("sort_order", 0)
    )


@router.post("/projects", response_model=Project)
async def create_project(project: Project, admin: dict = Depends(require_admin_auth)):
    query = """
        INSERT INTO projects (portfolio_id, title, description, url, 
                              image_url, technologies, sort_order)
        VALUES (:portfolio_id, :title, :description, :url, 
                :image_url, :technologies, :sort_order)
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
    row_dict = dict(row)
    technologies = row_dict.get("technologies", [])
    if isinstance(technologies, str):
        try:
            technologies = json.loads(technologies)
        except (json.JSONDecodeError, TypeError):
            technologies = []
    
    return Project(
        id=str(row_dict["id"]),
        portfolio_id=row_dict.get("portfolio_id", get_portfolio_id()),
        title=row_dict.get("title", ""),
        description=row_dict.get("description", ""),
        url=row_dict.get("url"),
        image_url=row_dict.get("image_url"),
        technologies=technologies,
        sort_order=row_dict.get("sort_order", 0)
    )


@router.put("/projects/{id}", response_model=Project)
async def update_project(id: str, project: Project, admin: dict = Depends(require_admin_auth)):
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
    
    row_dict = dict(row)
    technologies = row_dict.get("technologies", [])
    if isinstance(technologies, str):
        try:
            technologies = json.loads(technologies)
        except (json.JSONDecodeError, TypeError):
            technologies = []
    
    return Project(
        id=str(row_dict["id"]),
        portfolio_id=row_dict.get("portfolio_id", get_portfolio_id()),
        title=row_dict.get("title", ""),
        description=row_dict.get("description", ""),
        url=row_dict.get("url"),
        image_url=row_dict.get("image_url"),
        technologies=technologies,
        sort_order=row_dict.get("sort_order", 0)
    )


@router.delete("/projects/{id}")
async def delete_project(id: str, admin: dict = Depends(require_admin_auth)):
    query = "DELETE FROM projects WHERE id=:id"
    await database.execute(query, {"id": id})
    return {"deleted": True, "id": id}
