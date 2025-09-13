from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional, List
import json
import logging
import os
import shutil
from pathlib import Path

from auth import require_admin_auth, verify_token, is_authorized_user
from database import database, get_portfolio_id

router = APIRouter()
templates = Jinja2Templates(directory="templates")
logger = logging.getLogger(__name__)


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


@router.get("/work/", response_class=HTMLResponse)
async def work(request: Request):
    """Serve the work page - now a portfolio showcase listing"""
    user_authenticated = False
    user_email = None
    
    try:
        token = request.cookies.get("access_token")
        if token:
            payload = verify_token(token)
            email = payload.get("sub")
            if email and is_authorized_user(email):
                user_authenticated = True
                user_email = email
    except Exception:
        pass
    
    # Fetch projects for showcase listing
    try:
        portfolio_id = get_portfolio_id()
        logger.debug(f"work route: portfolio_id = {portfolio_id}")
        query = """
            SELECT id, title, description, url, image_url, technologies,
                   sort_order
            FROM projects
            WHERE portfolio_id = :portfolio_id
            ORDER BY sort_order, title
        """
        rows = await database.fetch_all(query, {"portfolio_id": portfolio_id})
        logger.debug(f"work route: found {len(rows)} rows")
        
        projects = []
        for row in rows:
            row_dict = dict(row)
            technologies = row_dict.get("technologies", [])
            if isinstance(technologies, str):
                try:
                    technologies = json.loads(technologies)
                except (json.JSONDecodeError, TypeError):
                    technologies = []
            
            # Create URL-safe project slug from title
            title = row_dict["title"]
            project_slug = title.lower().replace(" ", "-").replace("&", "and")
            project_slug = "".join(
                c for c in project_slug if c.isalnum() or c in "-"
            ).strip("-")
            
            # Check if showcase HTML file exists
            showcase_file_path = f"templates/showcase/{project_slug}.html"
            showcase_file_exists = os.path.exists(showcase_file_path)
            
            # Check for work-featured screenshot with specific naming convention
            screenshots_dir = Path(f"assets/screenshots/{project_slug}")
            work_featured_screenshot = None
            
            # Look for work-featured screenshot in common formats
            for ext in ['.png', '.jpg', '.jpeg', '.webp']:
                featured_path = screenshots_dir / f"work-featured{ext}"
                if featured_path.exists():
                    work_featured_screenshot = (
                        f"/assets/screenshots/{project_slug}/work-featured{ext}"
                    )
                    break
            
            # If no work-featured screenshot exists, create empty placeholder
            if not work_featured_screenshot:
                screenshots_dir.mkdir(parents=True, exist_ok=True)
                placeholder_path = screenshots_dir / "work-featured.png"
                if not placeholder_path.exists():
                    # Create empty placeholder file
                    placeholder_path.touch()
                work_featured_screenshot = (
                    f"/assets/screenshots/{project_slug}/work-featured.png"
                )
            
            projects.append({
                "id": str(row_dict["id"]),
                "title": row_dict["title"],
                "description": row_dict["description"],
                "url": row_dict.get("url"),
                "image_url": row_dict.get("image_url"),
                "technologies": technologies,
                "sort_order": row_dict.get("sort_order", 0),
                "slug": project_slug,
                "showcase_file_exists": showcase_file_exists,
                "screenshot_url": work_featured_screenshot
            })
    except Exception:
        projects = []
    
    return templates.TemplateResponse("work.html", {
        "request": request,
        "title": "Featured projects, and work - daniel blackburn",
        "current_page": "work",
        "user_authenticated": user_authenticated,
        "user_email": user_email,
        "projects": projects
    })


@router.get("/work/{project_slug}/", response_class=HTMLResponse)
async def project_detail(request: Request, project_slug: str):
    """Serve individual project pages"""
    return templates.TemplateResponse("project.html", {
        "request": request,
        "project_slug": project_slug,
        "title": "Project - daniel blackburn"
    })


@router.get("/resume")
@router.get("/resume/")
async def resume():
    """Serve resume PDF directly for browser viewing"""
    return FileResponse(
        path="assets/files/danielblackburn.pdf",
        media_type="application/pdf",
        filename="danielblackburn.pdf",
        headers={"Content-Disposition": "inline; filename=danielblackburn.pdf"}
    )


@router.get("/resume/download/")
async def resume_download():
    """Serve resume PDF as attachment for download."""
    return FileResponse(
        path="assets/files/danielblackburn.pdf",
        media_type="application/pdf",
        filename="danielblackburn.pdf",
        headers={
            "Content-Disposition": "attachment; filename=danielblackburn.pdf"
        }
    )


@router.get("/workadmin", response_class=HTMLResponse)
async def work_admin_page(
    request: Request,
    admin: dict = Depends(require_admin_auth)
):
    return templates.TemplateResponse("workadmin.html", {
        "request": request,
        "current_page": "workadmin",
        "user_info": admin,
        "user_authenticated": True,
        "user_email": admin.get("email", ""),
        "portfolio_id": get_portfolio_id()
    })


@router.get("/workitems", response_model=List[WorkItem])
async def list_workitems():
    try:
        from database import PORTFOLIO_ID
        portfolio_id = PORTFOLIO_ID
        query = """
            SELECT * FROM work_experience
            WHERE portfolio_id = :portfolio_id
            ORDER BY sort_order, start_date DESC
        """
        rows = await database.fetch_all(query, {"portfolio_id": portfolio_id})
        
        work_items = []
        for row in rows:
            row_dict = dict(row)
            work_item_data = {
                "id": str(row_dict.get("id", "")),
                "portfolio_id": str(
                    row_dict.get("portfolio_id", get_portfolio_id())
                ),
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
        print(f"Error in list_workitems: {e}")
        return []


@router.get("/workitems/{id}", response_model=WorkItem)
async def get_workitem(id: str, admin: dict = Depends(require_admin_auth)):
    from database import PORTFOLIO_ID
    portfolio_id = PORTFOLIO_ID
    query = """
        SELECT * FROM work_experience
        WHERE id=:id AND portfolio_id=:portfolio_id
    """
    row = await database.fetch_one(
        query, {"id": id, "portfolio_id": portfolio_id}
    )
    if not row:
        raise HTTPException(status_code=404, detail="Work item not found")
    row_dict = dict(row)
    if row_dict.get('id'):
        row_dict['id'] = str(row_dict['id'])
    return WorkItem(**row_dict)


@router.post("/workitems", response_model=WorkItem)
async def create_workitem(
    item: WorkItem, admin: dict = Depends(require_admin_auth)
):
    query = """
        INSERT INTO work_experience (
            portfolio_id, company, position, location, start_date, end_date,
            description, is_current, company_url, sort_order
        )
        VALUES (
            :portfolio_id, :company, :position, :location, :start_date,
            :end_date, :description, :is_current, :company_url, :sort_order
        )
        RETURNING *
    """
    from database import PORTFOLIO_ID
    values = item.dict(exclude_unset=True)
    values["portfolio_id"] = PORTFOLIO_ID
    row = await database.fetch_one(query, values)
    row_dict = dict(row)
    if row_dict.get('id'):
        row_dict['id'] = str(row_dict['id'])
    return WorkItem(**row_dict)


@router.put("/workitems/{id}", response_model=WorkItem)
async def update_workitem(
    id: str, item: WorkItem, admin: dict = Depends(require_admin_auth)
):
    query = """
        UPDATE work_experience SET
            company=:company, position=:position, location=:location,
            start_date=:start_date, end_date=:end_date,
            description=:description, is_current=:is_current,
            company_url=:company_url, sort_order=:sort_order
        WHERE id=:id RETURNING *
    """
    values = item.dict(exclude_unset=True)
    values["id"] = id
    row = await database.fetch_one(query, values)
    if not row:
        raise HTTPException(status_code=404, detail="Work item not found")
    row_dict = dict(row)
    if row_dict.get('id'):
        row_dict['id'] = str(row_dict['id'])
    return WorkItem(**row_dict)


@router.delete("/workitems/{id}")
async def delete_workitem(
    id: str, admin: dict = Depends(require_admin_auth)
):
    query = "DELETE FROM work_experience WHERE id=:id"
    await database.execute(query, {"id": id})
    return {"success": True}
