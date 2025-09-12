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
        
        # Check if a custom template exists for this project
        custom_template_path = f"templates/showcase/{project_slug}.html"
        template_name = f"showcase/{project_slug}.html"
        
        if not os.path.exists(custom_template_path):
            # Generate the template file
            await generate_project_template(project)
        
        return templates.TemplateResponse(template_name, {
            "request": request,
            "title": f"{project['title']} - Portfolio Showcase",
            "current_page": "work",
            "project": project
        })
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")


async def generate_project_template(project):
    """Generate a custom template file for a project"""
    # Generate a clean template without linting issues
    template_lines = [
        '{% extends "base.html" %}',
        '',
        '{% block title %}{{ project.title }} - Portfolio{% endblock %}',
        '',
        '{% block body_class %}showcase project-showcase{% endblock %}',
        '',
        '{% block content %}',
        '                <article class="bc clearfix">',
        '                    <section class="project-showcase-content">',
        '                        <div class="project-header">',
        '                            <div class="breadcrumb">',
        '                                <a href="/work/">Back</a>',
        '                            </div>',
        '                            <h1>{{ project.title }}</h1>',
        '                            <div class="project-meta">',
        '                                {% if project.url %}',
        '                                <a href="{{ project.url }}" ' +
        'target="_blank" class="btn-primary">',
        '                                    View Live Project',
        '                                </a>',
        '                                {% endif %}',
        '                            </div>',
        '                        </div>',
        '',
        '                        <div class="project-content">',
        '                            <div class="project-overview">',
        '                                <h2>Project Overview</h2>',
        '                                <p>{{ project.description }}</p>',
        '                            </div>',
        '',
        '                            {% if project.technologies %}',
        '                            <div class="project-tech">',
        '                                <h3>Technologies Used</h3>',
        '                                <div class="tech-tags-large">',
        '                                    {% for tech in ' +
        'project.technologies %}',
        '                                    <span class="tech-tag-large">' +
        '{{ tech }}</span>',
        '                                    {% endfor %}',
        '                                </div>',
        '                            </div>',
        '                            {% endif %}',
        '',
        '                            <div class="project-details">',
        '                                <h3>Technical Implementation</h3>',
        '                                <p>Modern development practices.</p>',
        '                            </div>',
        '',
        '                            <div class="project-navigation">',
        '                                <a href="/work/" ' +
        'class="btn-secondary">Back</a>',
        '                                {% if project.url %}',
        '                                <a href="{{ project.url }}" ' +
        'target="_blank" class="btn-primary">View Project</a>',
        '                                {% endif %}',
        '                            </div>',
        '                        </div>',
        '                    </section>',
        '                </article>',
        '            </div>',
        '            <footer class="footer" role="contentinfo">',
        '                <p class="copyright">© 2025 Blackburn.</p>',
        '            </footer>',
        '        </div>',
        '    </div>',
        '</body>',
        '</html>'
    ]
    
    template_content = '\n'.join(template_lines)
    
    # Create the template file
    template_path = f"templates/showcase/{project['slug']}.html"
    
    # Ensure the directory exists
    os.makedirs("templates/showcase", exist_ok=True)
    
    # Write the template file
    with open(template_path, "w", encoding="utf-8") as f:
        f.write(template_content)


@router.get("/showcase/complex_schema.svg")
async def showcase_complex_schema():
    """Serve the interactive complex_schema.svg file."""
    return FileResponse(
        path="assets/showcase/complex_schema.svg",
        media_type="image/svg+xml",
        filename="complex_schema.svg",
        headers={"Content-Disposition": "inline"}
    )
