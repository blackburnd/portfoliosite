from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
import json
import os

from database import database, get_portfolio_id

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/showcase/{project_slug}/", response_class=HTMLResponse)
async def showcase_project(request: Request, project_slug: str):
    """Serve individual project showcase pages"""
    try:
        # Log the incoming request for debugging
        print(f"DEBUG: showcase_project called with slug: {project_slug}")
        
        # Fetch project data by matching slug
        portfolio_id = get_portfolio_id()
        print(f"DEBUG: portfolio_id = {portfolio_id}")
        
        query = """
            SELECT id, title, description, url, image_url, technologies,
                   sort_order
            FROM projects
            WHERE portfolio_id = :portfolio_id
            ORDER BY sort_order, title
        """
        rows = await database.fetch_all(query, {"portfolio_id": portfolio_id})
        print(f"DEBUG: found {len(rows)} projects in database")
        
        project = None
        for i, row in enumerate(rows):
            row_dict = dict(row)
            # Create URL-safe project slug from title
            title = row_dict["title"]
            slug_base = title.lower().replace(" ", "-").replace("&", "and")
            generated_slug = "".join(
                c for c in slug_base if c.isalnum() or c in "-"
            ).strip("-")
            
            print(f"DEBUG: Project {i}: '{title}' -> '{generated_slug}'")
            
            if generated_slug == project_slug:
                print(f"DEBUG: MATCH! '{title}' matches '{project_slug}'")
                technologies = row_dict.get("technologies", [])
                if isinstance(technologies, str):
                    try:
                        technologies = json.loads(technologies)
                    except (json.JSONDecodeError, TypeError):
                        technologies = []
                
                project = {
                    "id": str(row_dict["id"]),
                    "title": row_dict["title"],
                    "description": row_dict["description"],
                    "url": row_dict.get("url"),
                    "image_url": row_dict.get("image_url"),
                    "technologies": technologies,
                    "sort_order": row_dict.get("sort_order", 0),
                    "slug": project_slug
                }
                break
        
        if not project:
            print(f"DEBUG: No project found for slug '{project_slug}'")
            raise HTTPException(status_code=404, detail="Project not found")
        
        print(f"DEBUG: Rendering template for project: {project['title']}")
        
        # Calculate navigation (previous/next projects)
        all_projects = []
        for i, row in enumerate(rows):
            row_dict = dict(row)
            title = row_dict["title"]
            slug_base = title.lower().replace(" ", "-").replace("&", "and")
            generated_slug = "".join(
                c for c in slug_base if c.isalnum() or c in "-"
            ).strip("-")
            
            all_projects.append({
                "title": title,
                "slug": generated_slug
            })
        
        # Find current project index and calculate prev/next
        current_index = None
        for i, proj in enumerate(all_projects):
            if proj["slug"] == project_slug:
                current_index = i
                break
        
        prev_project = None
        next_project = None
        if current_index is not None:
            if current_index > 0:
                prev_project = all_projects[current_index - 1]
            if current_index < len(all_projects) - 1:
                next_project = all_projects[current_index + 1]
        
        # Check if project-specific template exists, use generic otherwise
        project_template = f"showcase/{project_slug}.html"
        generic_template = "showcase/project.html"
        
        # Check if project-specific template file exists
        import os
        project_template_path = f"templates/{project_template}"
        if os.path.exists(project_template_path):
            template_to_use = project_template
            print(f"DEBUG: Using project-specific template: {template_to_use}")
        else:
            template_to_use = generic_template
            print(f"DEBUG: Using generic template: {template_to_use}")
        
        return templates.TemplateResponse(template_to_use, {
            "request": request,
            "title": f"{project['title']} - Portfolio Showcase",
            "current_page": "work",
            "project": project,
            "prev_project": prev_project,
            "next_project": next_project
        })
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"DEBUG: Exception in showcase_project: {str(e)}")
        print(f"DEBUG: Exception type: {type(e).__name__}")
        import traceback
        print(f"DEBUG: Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")


@router.get("/showcase/complex_schema.svg")
async def showcase_complex_schema(request: Request):
    """Serve the interactive complex_schema.svg file."""
    return FileResponse(
        path="assets/showcase/complex_schema.svg",
        media_type="image/svg+xml",
        filename="complex_schema.svg",
        headers={"Content-Disposition": "inline"}
    )


async def generate_project_template(project):
    """Generate a simple template file for a project using base template"""
    # Create the template file path
    template_path = f"templates/showcase/{project['slug']}.html"
    
    # Check if a custom template already exists - if so, don't overwrite it
    if os.path.exists(template_path):
        print(f"Custom template already exists for {project['slug']}, "
              f"skipping generation")
        return
    
    # Read the base showcase template
    with open("templates/showcase_template.html", "r", encoding="utf-8") as f:
        template_content = f.read()
    
    # Ensure the directory exists
    os.makedirs("templates/showcase", exist_ok=True)
    
    # Write the template file only if it doesn't exist
    with open(template_path, "w", encoding="utf-8") as f:
        f.write(template_content)
    
    print(f"Generated new template for {project['slug']}")
