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
        # Fetch project data by matching slug
        portfolio_id = get_portfolio_id()
        query = """
            SELECT id, title, description, url, image_url, technologies,
                   sort_order
            FROM projects
            WHERE portfolio_id = :portfolio_id
            ORDER BY sort_order, title
        """
        rows = await database.fetch_all(query, {"portfolio_id": portfolio_id})
        
        project = None
        for row in rows:
            row_dict = dict(row)
            # Create URL-safe project slug from title
            title = row_dict["title"]
            slug_base = title.lower().replace(" ", "-").replace("&", "and")
            generated_slug = "".join(
                c for c in slug_base if c.isalnum() or c in "-"
            ).strip("-")
            
            if generated_slug == project_slug:
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
            raise HTTPException(status_code=404, detail="Project not found")
        
        return templates.TemplateResponse("showcase/project.html", {
            "request": request,
            "title": f"{project['title']} - Portfolio Showcase",
            "current_page": "work",
            "project": project
        })
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")


@router.get("/showcase/complex_schema.svg")
async def showcase_complex_schema():
    """Serve the interactive complex_schema.svg file."""
    return FileResponse(
        path="assets/showcase/complex_schema.svg",
        media_type="image/svg+xml",
        filename="complex_schema.svg",
        headers={"Content-Disposition": "inline"}
    )


async def generate_project_template(project):
    """Generate a simple template file for a project using base template"""
    # Read the base showcase template
    with open("templates/showcase_template.html", "r", encoding="utf-8") as f:
        template_content = f.read()
    
    # Create the template file
    template_path = f"templates/showcase/{project['slug']}.html"
    
    # Ensure the directory exists
    os.makedirs("templates/showcase", exist_ok=True)
    
    # Write the template file
    with open(template_path, "w", encoding="utf-8") as f:
        f.write(template_content)
