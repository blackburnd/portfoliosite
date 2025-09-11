"""
Template Context Processor
Automatically injects site configuration into all templates
"""
from fastapi import Request
from site_config import SiteConfigManager


class TemplateContextProcessor:
    """Processes template context to inject site configuration"""
    
    @staticmethod
    async def inject_site_config(request: Request) -> dict:
        """Inject site configuration into template context"""
        try:
            # Get all site configuration
            config = await SiteConfigManager.get_all_config()
            
            # Create template context
            context = {
                "site": {
                    "title": config.get("site_title", "Professional Portfolio"),
                    "tagline": config.get("site_tagline", "Building Better Solutions Through Experience"),
                    "company_name": config.get("company_name", "Portfolio Systems"),
                    "copyright_name": config.get("copyright_name", "Portfolio Owner"),
                },
                "page_titles": {
                    "work": config.get("work_page_title", "Featured projects and work experience"),
                    "projects": config.get("projects_page_title", "Featured Projects"),
                    "admin_work": config.get("admin_work_title", "Work Items Admin"),
                    "admin_projects": config.get("admin_projects_title", "Projects Admin"),
                },
                "hero": {
                    "heading": config.get("hero_heading", "Building Better Solutions Through Experience"),
                    "description": config.get("hero_description", ""),
                    "quote": config.get("hero_quote", ""),
                },
                "about": {
                    "heading": config.get("about_heading", "About Me"),
                    "paragraph1": config.get("about_paragraph1", ""),
                    "paragraph2": config.get("about_paragraph2", ""),
                },
                "focus": {
                    "heading": config.get("focus_heading", "Embracing Innovation"),
                    "description": config.get("focus_description", ""),
                },
                "assets": {
                    "profile_image_path": config.get("profile_image_path", "/assets/files/profile.png"),
                    "profile_image_alt": config.get("profile_image_alt", "Professional headshot"),
                    "resume_filename": config.get("resume_filename", "resume.pdf"),
                },
                "oauth": {
                    "success_message": config.get("oauth_success_message", "You have successfully logged in to your portfolio."),
                    "source_name": config.get("oauth_source_name", "Portfolio OAuth API"),
                }
            }
            
            return context
            
        except Exception as e:
            print(f"Error injecting site config: {e}")
            # Return minimal fallback context
            return {
                "site": {
                    "title": "Professional Portfolio",
                    "tagline": "Building Better Solutions Through Experience",
                    "company_name": "Portfolio Systems",
                    "copyright_name": "Portfolio Owner",
                },
                "page_titles": {
                    "work": "Featured projects and work experience",
                    "projects": "Featured Projects",
                    "admin_work": "Work Items Admin",
                    "admin_projects": "Projects Admin",
                },
                "hero": {
                    "heading": "Building Better Solutions Through Experience",
                    "description": "",
                    "quote": "",
                },
                "about": {
                    "heading": "About Me",
                    "paragraph1": "",
                    "paragraph2": "",
                },
                "focus": {
                    "heading": "Embracing Innovation",
                    "description": "",
                },
                "assets": {
                    "profile_image_path": "/assets/files/profile.png",
                    "profile_image_alt": "Professional headshot",
                    "resume_filename": "resume.pdf",
                },
                "oauth": {
                    "success_message": "You have successfully logged in to your portfolio.",
                    "source_name": "Portfolio OAuth API",
                }
            }


# Helper function to create enhanced template context
async def create_template_context(request: Request, **additional_context) -> dict:
    """Create template context with site configuration injected"""
    site_context = await TemplateContextProcessor.inject_site_config(request)
    
    # Merge with additional context
    context = {
        "request": request,
        **site_context,
        **additional_context
    }
    
    return context
