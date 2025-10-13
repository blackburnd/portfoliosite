from fastapi import APIRouter, Request, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional, List
import json
import logging
import os
import shutil
from pathlib import Path

from auth import require_admin_auth
from database import database, get_portfolio_id

# Import showcase template generation
try:
    from app.routers.showcase import generate_project_template
except ImportError:
    # Fallback if showcase module not available
    async def generate_project_template(project):
        pass

router = APIRouter()
templates = Jinja2Templates(directory="templates")
logger = logging.getLogger(__name__)


class Project(BaseModel):
    id: Optional[str] = None
    portfolio_id: str
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
        from database import PORTFOLIO_ID
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
                portfolio_id=str(row_dict["portfolio_id"]),
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
        print(f"Error in list_projects: {e}")
        return []


@router.get("/projects/{id}", response_model=Project)
async def get_project(id: str, admin: dict = Depends(require_admin_auth)):
    from database import PORTFOLIO_ID
    portfolio_id = PORTFOLIO_ID
    query = """SELECT * FROM projects
               WHERE id = :id AND portfolio_id = :portfolio_id"""
    row = await database.fetch_one(
        query, {"id": id, "portfolio_id": portfolio_id}
    )
    
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
        portfolio_id=str(row_dict["portfolio_id"]),
        title=row_dict.get("title", ""),
        description=row_dict.get("description", ""),
        url=row_dict.get("url"),
        image_url=row_dict.get("image_url"),
        technologies=technologies,
        sort_order=row_dict.get("sort_order", 0)
    )


@router.post("/projects", response_model=Project)
async def create_project(
    project: Project, admin: dict = Depends(require_admin_auth)
):
    query = """
        INSERT INTO projects (portfolio_id, title, description, url,
                              image_url, technologies, sort_order)
        VALUES (:portfolio_id, :title, :description, :url,
                :image_url, :technologies, :sort_order)
        RETURNING *
    """
    
    technologies_json = json.dumps(project.technologies or [])
    
    row = await database.fetch_one(query, {
        "portfolio_id": get_portfolio_id(),
        "title": project.title,
        "description": project.description,
        "url": project.url,
        "image_url": project.image_url,
        "technologies": technologies_json,
        "sort_order": project.sort_order or 0
    })
    row_dict = dict(row)
    technologies = row_dict.get("technologies", [])
    if isinstance(technologies, str):
        try:
            technologies = json.loads(technologies)
        except (json.JSONDecodeError, TypeError):
            technologies = []
    
    project_result = Project(
        id=str(row_dict["id"]),
        portfolio_id=str(row_dict["portfolio_id"]),
        title=row_dict.get("title", ""),
        description=row_dict.get("description", ""),
        url=row_dict.get("url"),
        image_url=row_dict.get("image_url"),
        technologies=technologies,
        sort_order=row_dict.get("sort_order", 0)
    )
    
    # Generate showcase template for the new project
    try:
        title = project_result.title
        project_slug = title.lower().replace(" ", "-").replace("&", "and")
        project_slug = "".join(
            c for c in project_slug if c.isalnum() or c in "-"
        ).strip("-")
        
        project_data = {
            "id": project_result.id,
            "title": project_result.title,
            "description": project_result.description,
            "url": project_result.url,
            "image_url": project_result.image_url,
            "technologies": project_result.technologies,
            "sort_order": project_result.sort_order,
            "slug": project_slug
        }
        await generate_project_template(project_data)
    except Exception as e:
        # Don't fail project creation if template generation fails
        print(f"Template generation failed: {e}")
    
    return project_result


@router.put("/projects/{id}", response_model=Project)
async def update_project(
    id: str, project: Project, admin: dict = Depends(require_admin_auth)
):
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
    
    project_result = Project(
        id=str(row_dict["id"]),
        portfolio_id=str(row_dict["portfolio_id"]),
        title=row_dict.get("title", ""),
        description=row_dict.get("description", ""),
        url=row_dict.get("url"),
        image_url=row_dict.get("image_url"),
        technologies=technologies,
        sort_order=row_dict.get("sort_order", 0)
    )
    
    # Regenerate showcase template for the updated project
    try:
        title = project_result.title
        project_slug = title.lower().replace(" ", "-").replace("&", "and")
        project_slug = "".join(
            c for c in project_slug if c.isalnum() or c in "-"
        ).strip("-")
        
        project_data = {
            "id": project_result.id,
            "title": project_result.title,
            "description": project_result.description,
            "url": project_result.url,
            "image_url": project_result.image_url,
            "technologies": project_result.technologies,
            "sort_order": project_result.sort_order,
            "slug": project_slug
        }
        await generate_project_template(project_data)
    except Exception as e:
        # Don't fail project update if template generation fails
        print(f"Template regeneration failed: {e}")
    
    return project_result


# Screenshot Management Endpoints

@router.delete("/projects/delete-screenshot")
async def delete_screenshot(
    request_data: dict,
    admin: dict = Depends(require_admin_auth)
):
    """Delete a screenshot file"""
    project_slug = request_data.get('project_slug')
    filename = request_data.get('filename')
    
    if not all([project_slug, filename]):
        return JSONResponse({"success": False, "message": "Missing required fields"}, status_code=400)
    
    screenshots_dir = Path(f"assets/screenshots/{project_slug}")
    file_path = screenshots_dir / filename
    
    if not file_path.exists():
        return JSONResponse({"success": False, "message": "File not found"}, status_code=404)
    
    try:
        file_path.unlink()
        return JSONResponse({
            "success": True,
            "message": "Screenshot deleted successfully"
        })
    except Exception as e:
        return JSONResponse({"success": False, "message": f"Delete failed: {str(e)}"}, status_code=500)


@router.delete("/projects/{id}")
async def delete_project(id: str, admin: dict = Depends(require_admin_auth)):
    query = "DELETE FROM projects WHERE id=:id"
    await database.execute(query, {"id": id})
    return {"deleted": True, "id": id}

@router.get("/projects/screenshots/{project_slug}")
async def get_project_screenshots(project_slug: str, admin: dict = Depends(require_admin_auth)):
    """Get list of screenshots for a project"""
    screenshots_dir = Path(f"assets/screenshots/{project_slug}")
    
    if not screenshots_dir.exists():
        return []
    
    screenshots = []
    for file_path in screenshots_dir.glob("*"):
        if file_path.is_file() and file_path.suffix.lower() in ['.png', '.jpg', '.jpeg', '.webp']:
            screenshots.append({
                "filename": file_path.name,
                "name": file_path.stem.replace('-', ' ').title(),
                "size": file_path.stat().st_size,
                "path": str(file_path)
            })
    
    return screenshots


@router.post("/projects/upload-screenshot")
async def upload_screenshot(
    file: UploadFile = File(...),
    project_slug: str = Form(...),
    admin: dict = Depends(require_admin_auth)
):
    """Upload a screenshot for a project"""
    
    # Validate file type
    if not file.content_type.startswith('image/'):
        return JSONResponse({"success": False, "message": "File must be an image"}, status_code=400)
    
    # Validate file size (2MB limit)
    if file.size and file.size > 2 * 1024 * 1024:
        return JSONResponse({"success": False, "message": "File too large (max 2MB)"}, status_code=400)
    
    # Create screenshots directory
    screenshots_dir = Path(f"assets/screenshots/{project_slug}")
    screenshots_dir.mkdir(parents=True, exist_ok=True)
    
    # Save file with original name (or generate if needed)
    file_extension = Path(file.filename).suffix if file.filename else '.png'
    safe_filename = file.filename or f"screenshot{file_extension}"
    
    # Make filename safe
    safe_filename = "".join(c for c in safe_filename if c.isalnum() or c in '.-_').strip()
    
    file_path = screenshots_dir / safe_filename
    
    # Handle duplicate names
    counter = 1
    original_path = file_path
    while file_path.exists():
        stem = original_path.stem
        suffix = original_path.suffix
        file_path = screenshots_dir / f"{stem}_{counter}{suffix}"
        counter += 1
    
    try:
        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        return JSONResponse({
            "success": True, 
            "message": "Screenshot uploaded successfully",
            "filename": file_path.name
        })
    except Exception as e:
        return JSONResponse({"success": False, "message": f"Upload failed: {str(e)}"}, status_code=500)


@router.post("/projects/update-screenshot-name")
async def update_screenshot_name(
    request_data: dict,
    admin: dict = Depends(require_admin_auth)
):
    """Update the display name of a screenshot (renames file)"""
    project_slug = request_data.get('project_slug')
    filename = request_data.get('filename') 
    new_name = request_data.get('new_name')
    
    if not all([project_slug, filename, new_name]):
        return JSONResponse({"success": False, "message": "Missing required fields"}, status_code=400)
    
    screenshots_dir = Path(f"assets/screenshots/{project_slug}")
    old_path = screenshots_dir / filename
    
    if not old_path.exists():
        return JSONResponse({"success": False, "message": "File not found"}, status_code=404)
    
    # Create new filename from display name
    file_extension = old_path.suffix
    safe_new_name = "".join(c for c in new_name if c.isalnum() or c in ' -_').strip()
    safe_new_name = safe_new_name.replace(' ', '-').lower()
    new_filename = f"{safe_new_name}{file_extension}"
    new_path = screenshots_dir / new_filename
    
    # Avoid overwriting existing files
    if new_path.exists() and new_path != old_path:
        return JSONResponse({"success": False, "message": "A file with that name already exists"}, status_code=400)
    
    try:
        old_path.rename(new_path)
        return JSONResponse({
            "success": True,
            "message": "Name updated successfully",
            "new_filename": new_filename
        })
    except Exception as e:
        return JSONResponse({"success": False, "message": f"Rename failed: {str(e)}"}, status_code=500)


@router.post("/projects/replace-screenshot")
async def replace_screenshot(
    file: UploadFile = File(...),
    project_slug: str = Form(...),
    original_filename: str = Form(...),
    admin: dict = Depends(require_admin_auth)
):
    """Replace a screenshot file, keeping original as backup with timestamp"""
    
    # Validate file type
    if not file.content_type.startswith('image/'):
        return JSONResponse(
            {"success": False, "message": "File must be an image"},
            status_code=400
        )
    
    # Validate file size (2MB limit)
    if file.size and file.size > 2 * 1024 * 1024:
        return JSONResponse(
            {"success": False, "message": "File too large (max 2MB)"},
            status_code=400
        )
    
    screenshots_dir = Path(f"assets/screenshots/{project_slug}")
    original_file_path = screenshots_dir / original_filename
    
    if not original_file_path.exists():
        return JSONResponse(
            {"success": False, "message": "Original file not found"},
            status_code=404
        )
    
    try:
        # Create backup filename with timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_stem = original_file_path.stem
        file_suffix = original_file_path.suffix
        backup_filename = f"{file_stem}_{timestamp}{file_suffix}"
        backup_file_path = screenshots_dir / backup_filename
        
        # Rename original file to backup
        original_file_path.rename(backup_file_path)
        
        # Save new file with original filename
        with open(original_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        return JSONResponse({
            "success": True,
            "message": "Screenshot replaced successfully",
            "backup_filename": backup_filename,
            "new_filename": original_filename
        })
    except Exception as e:
        # If something went wrong, try to restore the original
        try:
            if backup_file_path.exists() and not original_file_path.exists():
                backup_file_path.rename(original_file_path)
        except Exception:
            pass  # Ignore restoration errors
        
        return JSONResponse(
            {"success": False, "message": f"Replace failed: {str(e)}"},
            status_code=500
        )


@router.post("/projects/rename-screenshot")
async def rename_screenshot(
    request: dict,
    admin: dict = Depends(require_admin_auth)
):
    """Rename a screenshot file with conflict resolution"""
    
    project_slug = request.get("project_slug")
    current_filename = request.get("current_filename")
    new_filename = request.get("new_filename")
    
    if not all([project_slug, current_filename, new_filename]):
        return JSONResponse(
            {"success": False, "message": "Missing required parameters"},
            status_code=400
        )
    
    try:
        from datetime import datetime
        import shutil
        
        # Paths
        screenshots_dir = Path(f"assets/screenshots/{project_slug}")
        current_path = screenshots_dir / current_filename
        new_path = screenshots_dir / new_filename
        
        # Validate current file exists
        if not current_path.exists():
            return JSONResponse(
                {"success": False,
                 "message": f"Current file {current_filename} not found"},
                status_code=404
            )
        
        # Handle naming conflicts
        conflict_resolved = False
        conflict_backup = None
        
        if new_path.exists() and new_path != current_path:
            # Create backup name with timestamp for conflicting file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            name_parts = new_filename.rsplit('.', 1)
            if len(name_parts) == 2:
                conflict_backup = (f"{name_parts[0]}_renamed_{timestamp}"
                                   f".{name_parts[1]}")
            else:
                conflict_backup = f"{new_filename}_renamed_{timestamp}"
            
            conflict_backup_path = screenshots_dir / conflict_backup
            
            # Move the conflicting file to backup name
            shutil.move(str(new_path), str(conflict_backup_path))
            conflict_resolved = True
        
        # Rename the current file to new name
        shutil.move(str(current_path), str(new_path))
        
        response_data = {
            "success": True,
            "message": (f"Screenshot renamed from {current_filename} "
                       f"to {new_filename}"),
            "old_filename": current_filename,
            "new_filename": new_filename
        }
        
        if conflict_resolved:
            response_data["conflict_resolved"] = True
            response_data["conflict_backup"] = conflict_backup
        
        return JSONResponse(response_data)
        
    except Exception as e:
        logger.error(f"Error renaming screenshot: {str(e)}")
        return JSONResponse(
            {"success": False, "message": f"Rename failed: {str(e)}"},
            status_code=500
        )


@router.get("/other_projects/", response_class=HTMLResponse)
async def other_projects(request: Request):
    """Serve the other projects page"""
    return templates.TemplateResponse("other_projects.html", {
        "request": request,
        "title": "Other Projects - Daniel Blackburn",
        "current_page": "other_projects"
    })
