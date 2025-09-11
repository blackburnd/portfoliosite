#!/usr/bin/env python3
"""
Portfolio Data Population Script
Extracts current hardcoded content from HTML templates 
and populates the database
"""

import asyncio
import os
import sys

sys.path.append(os.path.dirname(__file__))

from database import database, init_database, get_portfolio_id
from site_config import SiteConfigManager


async def populate_portfolio_data():
    """Populate the database with current portfolio data from HTML templates"""
    
    await init_database()
    portfolio_id = get_portfolio_id()
    
    print(f"Populating portfolio data for portfolio_id: {portfolio_id}")
    
    # 1. Update main portfolio record
    await update_portfolio_record(portfolio_id)
    
    # 2. Add work experience data
    await add_work_experience(portfolio_id)
    
    # 3. Add projects data
    await add_projects(portfolio_id)
    
    # 4. Add site configuration data
    await add_site_config()
    
    print("✅ Portfolio data population completed!")


async def update_portfolio_record(portfolio_id: str):
    """Update the main portfolio record with current data"""
    print("📝 Updating portfolio record...")
    
    query = """
    UPDATE portfolios SET
        name = :name,
        title = :title,
        bio = :bio,
        tagline = :tagline,
        profile_image = :profile_image,
        email = :email,
        phone = :phone,
        vcard = :vcard,
        resume_url = :resume_url,
        resume_download = :resume_download,
        github = :github,
        twitter = :twitter,
        skills = :skills,
        updated_at = NOW()
    WHERE portfolio_id = :portfolio_id
    """
    
    # Data extracted from current HTML templates
    portfolio_data = {
        "portfolio_id": portfolio_id,
        "name": "Daniel Blackburn",
        "title": "Software Developer & Cloud Engineer",
        "bio": "With experience that expands throughout University IT departments, corporate banking environments, and agile remote startup companies, I have learned that foundational knowledge combined with effective communication creates a lasting impact. I thrive by embracing continuous growth and approaching every challenge with the mindset of a lifelong learner.",
        "tagline": "Curious. Academic. & Novel Solutions Work.",
        "profile_image": "/assets/files/daniel2.png",
        "email": "danielb@blackburnsystems.com",
        "phone": "305-773-3923",
        "vcard": "daniel-blackburn.vcf",
        "resume_url": "/resume",
        "resume_download": "daniel-blackburn-resume.pdf",
        "github": "https://github.com/blackburnd",
        "twitter": "@blackburnd",
        "skills": ["Python", "FastAPI", "GraphQL", "PostgreSQL", "Cloud Computing", "CI/CD", "JavaScript", "Docker", "AI Integration", "System Architecture"]
    }
    
    await database.execute(query, portfolio_data)
    print("✅ Portfolio record updated")


async def add_work_experience(portfolio_id: str):
    """Add work experience data"""
    print("💼 Adding work experience...")
    
    # Clear existing work experience for this portfolio
    await database.execute(
        "DELETE FROM work_experience WHERE portfolio_id = :portfolio_id",
        {"portfolio_id": portfolio_id}
    )
    
    work_experiences = [
        {
            "portfolio_id": portfolio_id,
            "company": "Blackburn Systems",
            "position": "Senior Software Developer & Cloud Architect",
            "location": "Remote",
            "start_date": "2020",
            "end_date": None,
            "description": "Building innovative solutions with modern technologies including FastAPI, GraphQL, and cloud infrastructure. Leading development of automated deployment pipelines and scalable web applications. Specializing in AI integration and system architecture for performance optimization.",
            "is_current": True,
            "company_url": "https://blackburnsystems.com",
            "sort_order": 1
        },
        {
            "portfolio_id": portfolio_id,
            "company": "Previous Corporate Banking Role",
            "position": "Solutions Architect",
            "location": "Corporate Environment",
            "start_date": "2015",
            "end_date": "2020",
            "description": "Architected and implemented enterprise solutions in corporate banking environments. Developed secure, scalable systems for financial operations with emphasis on reliability and compliance.",
            "is_current": False,
            "company_url": None,
            "sort_order": 2
        },
        {
            "portfolio_id": portfolio_id,
            "company": "University IT Department",
            "position": "Software Developer",
            "location": "University Campus",
            "start_date": "2010",
            "end_date": "2015", 
            "description": "Developed and maintained IT systems for university operations. Gained foundational experience in collaborative development and educational technology solutions.",
            "is_current": False,
            "company_url": None,
            "sort_order": 3
        }
    ]
    
    for work in work_experiences:
        query = """
        INSERT INTO work_experience (
            portfolio_id, company, position, location, start_date, end_date,
            description, is_current, company_url, sort_order
        ) VALUES (
            :portfolio_id, :company, :position, :location, :start_date, :end_date,
            :description, :is_current, :company_url, :sort_order
        )
        """
        await database.execute(query, work)
    
    print(f"✅ Added {len(work_experiences)} work experiences")

async def add_projects(portfolio_id: str):
    """Add projects data"""
    print("🚀 Adding projects...")
    
    # Clear existing projects for this portfolio
    await database.execute(
        "DELETE FROM projects WHERE portfolio_id = :portfolio_id",
        {"portfolio_id": portfolio_id}
    )
    
    projects = [
        {
            "portfolio_id": portfolio_id,
            "title": "AI-Enhanced Portfolio Platform",
            "description": "Modern portfolio website built with FastAPI and GraphQL, featuring AI integration for enhanced user experience. Includes automated deployment, OAuth authentication, and dynamic content management through a comprehensive admin interface.",
            "url": "https://blackburnsystems.com",
            "image_url": None,
            "technologies": ["FastAPI", "GraphQL", "PostgreSQL", "AI Integration", "OAuth", "JavaScript", "CSS"],
            "sort_order": 1
        },
        {
            "portfolio_id": portfolio_id,
            "title": "Cloud Infrastructure Automation",
            "description": "Automated cloud deployment pipelines with CI/CD integration. Features include infrastructure as code, automated testing, monitoring, and scalable architecture for production environments.",
            "url": "https://github.com/blackburnd",
            "image_url": None,
            "technologies": ["Cloud Computing", "CI/CD", "Docker", "Infrastructure as Code", "Monitoring"],
            "sort_order": 2
        },
        {
            "portfolio_id": portfolio_id,
            "title": "Enterprise System Architecture",
            "description": "Designed and implemented scalable enterprise solutions with emphasis on security, reliability, and performance. Focused on creating maintainable systems that scale with business needs.",
            "url": None,
            "image_url": None,
            "technologies": ["System Architecture", "Enterprise Solutions", "Security", "Performance Optimization"],
            "sort_order": 3
        }
    ]
    
    for project in projects:
        query = """
        INSERT INTO projects (
            portfolio_id, title, description, url, image_url, technologies, sort_order
        ) VALUES (
            :portfolio_id, :title, :description, :url, :image_url, :technologies, :sort_order
        )
        """
        await database.execute(query, project)
    
    print(f"✅ Added {len(projects)} projects")

async def add_site_config():
    """Add site configuration data"""
    print("⚙️  Adding site configuration...")
    
    # Site configuration from current templates
    config_data = {
        # Personal Information
        "full_name": "Daniel Blackburn",
        "professional_title": "Software Developer & Cloud Engineer",
        "email": "danielb@blackburnsystems.com",
        "phone": "305-773-3923",
        "location": "Remote",
        "bio": "With over two decades of experience solving problems and architecting solutions, I appreciate the deep knowledge that comes from curiosity, trial, and hands-on problem solving.",
        "tagline": "Curious. Academic. & Novel Solutions Work.",
        "linkedin_url": "https://linkedin.com/in/blackburnd",
        "github_url": "https://github.com/blackburnd",
        
        # Site Settings
        "site_title": "Daniel Blackburn",
        "site_description": "Software Developer & Cloud Engineer specializing in modern web technologies and AI integration",
        "company_name": "Blackburn Systems",
        "copyright_text": "© 2025 Blackburn.",
        "favicon_url": "/favicon.ico",
        "logo_url": "/assets/files/daniel2.png",
        
        # Navigation Labels
        "nav_home_label": "Overview",
        "nav_work_label": "Select Work",
        "nav_projects_label": "Projects",
        "nav_contact_label": "we should talk",
        "nav_admin_label": "Administration",
        
        # Contact Information
        "contact_email": "danielb@blackburnsystems.com",
        "contact_phone": "305-773-3923",
        "contact_form_action": "/contact/submit",
        "contact_form_method": "POST",
        
        # Social Media
        "social_linkedin": "https://linkedin.com/in/blackburnd",
        "social_github": "https://github.com/blackburnd",
        "social_pypi": "https://pypi.org/user/blackburnd/",
        "social_resume": "/resume",
        
        # Content Sections
        "hero_heading": "Building Better Solutions Through Experience",
        "hero_description": "With experience that expands throughout University IT departments, corporate banking environments, and agile remote startup companies, I have learned that foundational knowledge combined with effective communication creates a lasting impact.",
        "about_heading": "About Me",
        "about_content": "With over two decades of experience solving problems and architecting solutions, I appreciate the deep knowledge that comes from curiosity, trial, and hands-on problem solving. My career has taken me through diverse environments where I've learned that the best solutions often require looking beyond the obvious tools.",
        "ai_focus_heading": "Embracing the AI Revolution",
        "ai_focus_content": "Things are changing fast, and it's an incredibly exciting time to be skilled in software development—especially when you have a clear sense of what 'correct' looks like. I think of using AI as a pair programmer like working with a mischievous djinn: it's resourceful but often unreliable, yet with clear guardrails, good oversight, and thoughtful follow-up, it can provide surprisingly valuable solutions."
    }
    
    for key, value in config_data.items():
        await SiteConfigManager.set_config(
            key=key,
            value=str(value),
            description=f"Site configuration for {key}"
        )
    
    print(f"✅ Added {len(config_data)} site configuration items")

if __name__ == "__main__":
    asyncio.run(populate_portfolio_data())
