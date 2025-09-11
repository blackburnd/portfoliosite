"""
Site Configuration Management Router
Provides Through-The-Web configuration forms for all site settings
"""

from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import logging

from auth import require_admin_auth
from site_config import SiteConfigManager

router = APIRouter()
templates = Jinja2Templates(directory="templates")
logger = logging.getLogger(__name__)

# Configuration categories for form organization
CONFIG_CATEGORIES = {
    "personal": {
        "title": "Personal Information",
        "description": "Your name, title, and personal branding",
        "icon": "👤",
        "configs": [
            "full_name", "professional_title", "email", "phone",
            "location", "bio", "tagline", "linkedin_url", "github_url"
        ]
    },
    "site": {
        "title": "Site Settings",
        "description": "General website configuration and branding",
        "icon": "🌐",
        "configs": [
            "site_title", "site_description", "company_name",
            "copyright_text", "favicon_url", "logo_url"
        ]
    },
    "navigation": {
        "title": "Navigation & Menu",
        "description": "Navigation labels and menu structure",
        "icon": "🧭",
        "configs": [
            "nav_home_label", "nav_work_label", "nav_projects_label",
            "nav_contact_label", "nav_admin_label"
        ]
    },
    "contact": {
        "title": "Contact Information",
        "description": "Contact form and communication settings",
        "icon": "📧",
        "configs": [
            "contact_email", "contact_phone", "contact_address",
            "contact_form_title", "contact_form_subtitle",
            "contact_success_message"
        ]
    },
    "social": {
        "title": "Social Media",
        "description": "Social media links and profiles",
        "icon": "📱",
        "configs": [
            "twitter_url", "linkedin_url", "github_url", "instagram_url",
            "facebook_url", "youtube_url", "portfolio_url"
        ]
    },
    "content": {
        "title": "Page Content",
        "description": "Homepage and page-specific content",
        "icon": "📝",
        "configs": [
            "homepage_hero_title", "homepage_hero_subtitle",
            "homepage_about_text", "work_page_title", "work_page_subtitle",
            "projects_page_title", "projects_page_subtitle"
        ]
    }
}


@router.get("/admin/config", response_class=HTMLResponse)
async def config_overview(request: Request, _=Depends(require_admin_auth)):
    """Configuration overview page showing all categories"""
    try:
        # Add debug logging
        from database import get_portfolio_id
        portfolio_id = get_portfolio_id()
        logger.info(f"Portfolio ID for config: {portfolio_id}")
        
        if not portfolio_id:
            logger.error("Portfolio ID is None, cannot load configuration")
            raise HTTPException(
                status_code=500,
                detail="Portfolio ID not available"
            )
        
        config_manager = SiteConfigManager()
        logger.info("SiteConfigManager created successfully")
        
        all_config = await config_manager.get_all_config()
        logger.info(f"Loaded {len(all_config)} configuration values")

        # Organize config by categories
        categorized_config = {}
        for category_key, category_info in CONFIG_CATEGORIES.items():
            categorized_config[category_key] = {
                "info": category_info,
                "config_values": {}
            }
            for config_key in category_info["configs"]:
                config_value = all_config.get(config_key, "")
                cat_config = categorized_config[category_key]["config_values"]
                cat_config[config_key] = config_value

        logger.info("Configuration data organized successfully")
        
        return templates.TemplateResponse(
            "admin/config_overview.html",
            {
                "request": request,
                "categories": categorized_config,
                "total_configs": len(all_config)
            }
        )
    except Exception as e:
        logger.error(f"Error loading config overview: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500, detail=f"Failed to load configuration: {str(e)}"
        )


@router.get("/admin/config/{category}", response_class=HTMLResponse)
async def config_category_form(
    request: Request,
    category: str,
    _=Depends(require_admin_auth)
):
    """Show configuration form for a specific category"""
    if category not in CONFIG_CATEGORIES:
        raise HTTPException(
            status_code=404, detail="Configuration category not found"
        )

    try:
        config_manager = SiteConfigManager()
        category_info = CONFIG_CATEGORIES[category]

        # Get current values for this category
        current_values = {}
        for config_key in category_info["configs"]:
            current_values[config_key] = await config_manager.get_config(
                config_key, ""
            )

        return templates.TemplateResponse(
            "admin/config_form.html",
            {
                "request": request,
                "category": category,
                "category_info": category_info,
                "current_values": current_values
            }
        )
    except Exception as e:
        logger.error(f"Error loading config form for {category}: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to load configuration form"
        )


@router.post("/admin/config/{category}")
async def update_category_config(
    request: Request,
    category: str,
    _=Depends(require_admin_auth)
):
    """Update configuration values for a specific category"""
    if category not in CONFIG_CATEGORIES:
        raise HTTPException(
            status_code=404, detail="Configuration category not found"
        )

    try:
        form_data = await request.form()
        config_manager = SiteConfigManager()
        category_info = CONFIG_CATEGORIES[category]

        # Update each configuration value
        updated_count = 0
        for config_key in category_info["configs"]:
            if config_key in form_data:
                value = form_data[config_key].strip()
                await config_manager.set_config(config_key, value)
                updated_count += 1

        logger.info(
            f"Updated {updated_count} config values in category {category}"
        )

        # Redirect back to the form with success message
        return RedirectResponse(
            url=f"/admin/config/{category}?success=true&updated={updated_count}",  # noqa: E501
            status_code=303
        )

    except Exception as e:
        logger.error(f"Error updating config for {category}: {e}")
        return RedirectResponse(
            url=f"/admin/config/{category}?error=true",
            status_code=303
        )


@router.get("/admin/config/{category}/reset")
async def reset_category_config(
    request: Request,
    category: str,
    _=Depends(require_admin_auth)
):
    """Reset configuration values for a category to defaults"""
    if category not in CONFIG_CATEGORIES:
        raise HTTPException(
            status_code=404, detail="Configuration category not found"
        )

    try:
        config_manager = SiteConfigManager()
        category_info = CONFIG_CATEGORIES[category]

        # Reset each configuration value to empty
        reset_count = 0
        for config_key in category_info["configs"]:
            await config_manager.set_config(config_key, "")
            reset_count += 1

        logger.info(
            f"Reset {reset_count} config values in category {category}"
        )

        return RedirectResponse(
            url=f"/admin/config/{category}?reset=true&count={reset_count}",
            status_code=303
        )

    except Exception as e:
        logger.error(f"Error resetting config for {category}: {e}")
        return RedirectResponse(
            url=f"/admin/config/{category}?error=true",
            status_code=303
        )


@router.post("/admin/config/bulk-update")
async def bulk_update_config(
    request: Request,
    _=Depends(require_admin_auth)
):
    """Bulk update multiple configuration values"""
    try:
        form_data = await request.form()
        config_manager = SiteConfigManager()

        updated_count = 0
        for key, value in form_data.items():
            if key.startswith("config_"):
                config_key = key[7:]  # Remove "config_" prefix
                await config_manager.set_config(config_key, value.strip())
                updated_count += 1

        logger.info(f"Bulk updated {updated_count} configuration values")

        return RedirectResponse(
            url=f"/admin/config?bulk_success=true&updated={updated_count}",
            status_code=303
        )

    except Exception as e:
        logger.error(f"Error in bulk config update: {e}")
        return RedirectResponse(
            url="/admin/config?error=true",
            status_code=303
        )
