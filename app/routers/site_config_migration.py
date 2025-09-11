"""
Web-based Site Configuration Migration Route
Extracts existing content and populates configuration tables
"""
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import re
import os
from pathlib import Path
from typing import Dict, List, Tuple

from auth import require_admin_auth
from database import database, get_portfolio_id

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/admin/migrate-site-config", response_class=HTMLResponse)
async def show_migration_page(
    request: Request,
    admin: dict = Depends(require_admin_auth)
):
    """Show the migration interface"""
    return templates.TemplateResponse("site_config_migration.html", {
        "request": request,
        "current_page": "site_config_migration",
        "user_info": admin,
        "user_authenticated": True,
        "user_email": admin.get("email", "")
    })


@router.post("/admin/migrate-site-config/extract")
async def extract_existing_content(
    request: Request,
    admin: dict = Depends(require_admin_auth)
):
    """Extract existing content from templates and code"""
    
    try:
        extracted_content = {}
        
        # Extract from templates
        template_content = await _extract_template_content()
        extracted_content.update(template_content)
        
        # Extract from route files  
        route_content = await _extract_route_content()
        extracted_content.update(route_content)
        
        # Extract from main.py
        main_content = await _extract_main_content()
        extracted_content.update(main_content)
        
        return {
            "status": "success",
            "extracted_content": extracted_content,
            "total_items": len(extracted_content)
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to extract content: {str(e)}"
        }


@router.post("/admin/migrate-site-config/apply")
async def apply_migration(
    request: Request,
    admin: dict = Depends(require_admin_auth)
):
    """Apply the migration with extracted content"""
    
    try:
        # Get portfolio ID
        portfolio_id = get_portfolio_id()
        if not portfolio_id:
            raise HTTPException(status_code=500, detail="No portfolio ID found")
        
        # Step 1: Create tables
        await _create_site_config_table()
        
        # Step 2: Extract current content
        extracted_content = {}
        template_content = await _extract_template_content()
        extracted_content.update(template_content)
        
        route_content = await _extract_route_content()
        extracted_content.update(route_content)
        
        main_content = await _extract_main_content()
        extracted_content.update(main_content)
        
        # Step 3: Populate configuration table
        inserted_count = await _populate_site_config(portfolio_id, extracted_content)
        
        return {
            "status": "success",
            "message": f"Migration completed successfully! Created site_config table and inserted {inserted_count} configuration values.",
            "portfolio_id": portfolio_id,
            "inserted_count": inserted_count,
            "extracted_content": extracted_content
        }
        
    except Exception as e:
        return {
            "status": "error", 
            "message": f"Migration failed: {str(e)}"
        }


async def _create_site_config_table():
    """Create the site_config table and related objects"""
    
    # Create table
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS site_config (
        id SERIAL PRIMARY KEY,
        portfolio_id UUID NOT NULL REFERENCES portfolios(portfolio_id) ON DELETE CASCADE,
        config_key VARCHAR(100) NOT NULL,
        config_value TEXT,
        description TEXT,
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW(),
        UNIQUE(portfolio_id, config_key)
    );
    """
    await database.execute(create_table_sql)
    
    # Create index
    index_sql = """
    CREATE INDEX IF NOT EXISTS idx_site_config_portfolio_key 
    ON site_config(portfolio_id, config_key);
    """
    await database.execute(index_sql)
    
    # Create trigger function and trigger
    trigger_sql = """
    CREATE OR REPLACE FUNCTION update_site_config_updated_at()
    RETURNS TRIGGER AS $$
    BEGIN
        NEW.updated_at = NOW();
        RETURN NEW;
    END;
    $$ language 'plpgsql';

    DROP TRIGGER IF EXISTS update_site_config_updated_at ON site_config;
    CREATE TRIGGER update_site_config_updated_at
        BEFORE UPDATE ON site_config
        FOR EACH ROW
        EXECUTE FUNCTION update_site_config_updated_at();
    """
    await database.execute(trigger_sql)


async def _extract_template_content() -> Dict[str, str]:
    """Extract content from template files"""
    content = {}
    
    try:
        # Extract from index.html
        index_path = Path("templates/index.html")
        if index_path.exists():
            with open(index_path, 'r', encoding='utf-8') as f:
                index_content = f.read()
            
            # Extract hero heading
            hero_match = re.search(r'<h2>([^<]+)</h2>', index_content)
            if hero_match:
                content['hero_heading'] = hero_match.group(1).strip()
            
            # Extract alt text from profile image
            alt_match = re.search(r'alt="([^"]+)"', index_content)
            if alt_match:
                content['profile_image_alt'] = alt_match.group(1).strip()
            
            # Extract about heading
            about_match = re.search(r'<h3>About Me</h3>', index_content)
            if about_match:
                content['about_heading'] = 'About Me'
            
            # Extract focus heading
            focus_match = re.search(r'<h3>([^<]*AI Revolution[^<]*)</h3>', index_content)
            if focus_match:
                content['focus_heading'] = focus_match.group(1).strip()
            elif re.search(r'<h3>Embracing', index_content):
                content['focus_heading'] = 'Embracing the AI Revolution'
        
        # Extract from workadmin.html
        workadmin_path = Path("templates/workadmin.html")
        if workadmin_path.exists():
            with open(workadmin_path, 'r', encoding='utf-8') as f:
                workadmin_content = f.read()
            
            title_match = re.search(r'<title>([^<]+)</title>', workadmin_content)
            if title_match:
                content['admin_work_title'] = title_match.group(1).strip()
            
            copyright_match = re.search(r'© \d+ ([^<.]+)', workadmin_content)
            if copyright_match:
                content['copyright_name'] = copyright_match.group(1).strip()
        
        # Extract from projectsadmin.html
        projectsadmin_path = Path("templates/projectsadmin.html")
        if projectsadmin_path.exists():
            with open(projectsadmin_path, 'r', encoding='utf-8') as f:
                projectsadmin_content = f.read()
            
            title_match = re.search(r'<title>([^<]+)</title>', projectsadmin_content)
            if title_match:
                content['admin_projects_title'] = title_match.group(1).strip()
        
    except Exception as e:
        print(f"Error extracting template content: {e}")
    
    return content


async def _extract_route_content() -> Dict[str, str]:
    """Extract content from route files"""
    content = {}
    
    try:
        # Extract from work.py
        work_path = Path("app/routers/work.py")
        if work_path.exists():
            with open(work_path, 'r', encoding='utf-8') as f:
                work_content = f.read()
            
            # Extract work page title
            title_match = re.search(r'"title":\s*"([^"]+)"', work_content)
            if title_match and 'work' in title_match.group(1).lower():
                content['work_page_title'] = title_match.group(1).strip()
            
            # Extract resume filename
            filename_match = re.search(r'filename="([^"]+\.pdf)"', work_content)
            if filename_match:
                content['resume_filename'] = filename_match.group(1).strip()
        
        # Extract from projects.py
        projects_path = Path("app/routers/projects.py")
        if projects_path.exists():
            with open(projects_path, 'r', encoding='utf-8') as f:
                projects_content = f.read()
            
            title_match = re.search(r'"title":\s*"([^"]*Projects[^"]*)"', projects_content)
            if title_match:
                content['projects_page_title'] = title_match.group(1).strip()
        
        # Extract from oauth.py
        oauth_path = Path("app/routers/oauth.py")
        if oauth_path.exists():
            with open(oauth_path, 'r', encoding='utf-8') as f:
                oauth_content = f.read()
            
            # Extract OAuth success message
            success_match = re.search(r'You have successfully logged in to ([^<.]+)', oauth_content)
            if success_match:
                content['oauth_success_message'] = f"You have successfully logged in to your portfolio."
            
            # Extract OAuth source name
            source_match = re.search(r'"source":\s*"([^"]*OAuth[^"]*)"', oauth_content)
            if source_match:
                content['oauth_source_name'] = source_match.group(1).strip()
        
    except Exception as e:
        print(f"Error extracting route content: {e}")
    
    return content


async def _extract_main_content() -> Dict[str, str]:
    """Extract content from main.py"""
    content = {}
    
    try:
        main_path = Path("main.py")
        if main_path.exists():
            with open(main_path, 'r', encoding='utf-8') as f:
                main_content = f.read()
            
            # Extract site title
            title_match = re.search(r'title="([^"]+)"', main_content)
            if title_match:
                content['site_title'] = title_match.group(1).strip()
            
            # Extract description for tagline
            desc_match = re.search(r'description=\s*"([^"]+)"', main_content)
            if desc_match:
                desc = desc_match.group(1).strip()
                # Extract company name from description
                if 'Daniel Blackburn' in desc:
                    content['site_tagline'] = 'Building Better Solutions Through Experience'
                else:
                    content['site_tagline'] = desc
        
        # Extract from portfolio.service
        service_path = Path("portfolio.service")
        if service_path.exists():
            with open(service_path, 'r', encoding='utf-8') as f:
                service_content = f.read()
            
            desc_match = re.search(r'Description=([^\n]+)', service_content)
            if desc_match:
                content['service_description'] = desc_match.group(1).strip()
            
            user_match = re.search(r'User=([^\n]+)', service_content)
            if user_match:
                content['service_user'] = user_match.group(1).strip()
    
    except Exception as e:
        print(f"Error extracting main content: {e}")
    
    return content


async def _populate_site_config(portfolio_id: str, extracted_content: Dict[str, str]) -> int:
    """Populate the site_config table with extracted content"""
    
    # Default configuration with extracted content
    config_data = [
        ('site_title', extracted_content.get('site_title', 'Professional Portfolio'), 'Main site title'),
        ('site_tagline', extracted_content.get('site_tagline', 'Building Better Solutions Through Experience'), 'Hero tagline'),
        ('company_name', 'Portfolio Systems', 'Company/brand name'),
        ('copyright_name', extracted_content.get('copyright_name', 'Portfolio Owner'), 'Copyright name'),
        ('work_page_title', extracted_content.get('work_page_title', 'Featured projects and work experience'), 'Work page title'),
        ('projects_page_title', extracted_content.get('projects_page_title', 'Featured Projects'), 'Projects page title'),
        ('admin_work_title', extracted_content.get('admin_work_title', 'Work Items Admin'), 'Work admin page title'),
        ('admin_projects_title', extracted_content.get('admin_projects_title', 'Projects Admin'), 'Projects admin page title'),
        ('hero_heading', extracted_content.get('hero_heading', 'Building Better Solutions Through Experience'), 'Hero heading'),
        ('about_heading', extracted_content.get('about_heading', 'About Me'), 'About section heading'),
        ('focus_heading', extracted_content.get('focus_heading', 'Embracing Innovation'), 'Focus section heading'),
        ('profile_image_path', '/assets/files/profile.png', 'Profile image path'),
        ('profile_image_alt', extracted_content.get('profile_image_alt', 'Professional headshot'), 'Profile image alt text'),
        ('resume_filename', extracted_content.get('resume_filename', 'resume.pdf'), 'Resume filename'),
        ('oauth_success_message', extracted_content.get('oauth_success_message', 'You have successfully logged in to your portfolio.'), 'OAuth success message'),
        ('oauth_source_name', extracted_content.get('oauth_source_name', 'Portfolio OAuth API'), 'OAuth source name'),
        ('service_description', extracted_content.get('service_description', 'Professional Portfolio FastAPI Application'), 'Service description'),
        ('service_user', extracted_content.get('service_user', 'portfolio'), 'Service user'),
    ]
    
    insert_sql = """
    INSERT INTO site_config (portfolio_id, config_key, config_value, description)
    VALUES (:portfolio_id, :config_key, :config_value, :description)
    ON CONFLICT (portfolio_id, config_key) 
    DO UPDATE SET 
        config_value = EXCLUDED.config_value,
        description = EXCLUDED.description,
        updated_at = NOW()
    """
    
    inserted_count = 0
    for config_key, config_value, description in config_data:
        await database.execute(insert_sql, {
            "portfolio_id": portfolio_id,
            "config_key": config_key,
            "config_value": config_value,
            "description": description
        })
        inserted_count += 1
    
    return inserted_count
