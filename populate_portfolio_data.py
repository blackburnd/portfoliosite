#!/usr/bin/env python3
"""
Portfolio Data Population Script
Extracts current hardcoded content from HTML templates 
and populates the database
"""

import asyncio
import json
import os
import sys

sys.path.append(os.path.dirname(__file__))

from database import database, init_database, get_portfolio_id
from site_config import SiteConfigManager


async def populate_portfolio_data():
    """Populate the database with current portfolio data from HTML templates"""
    
    await init_database()
    portfolio_id = get_portfolio_id()
    
    print(f"🎯 Populating portfolio data for portfolio_id: {portfolio_id}")
    
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
    
    # Data extracted from templates/index.html
    portfolio_data = {
        "name": "Daniel Blackburn",
        "title": "Software Developer & Cloud Engineer", 
        "bio": "Passionate software developer with expertise in cloud technologies, automation, and modern web development. Experienced in building scalable applications and robust CI/CD pipelines.",
        "tagline": "Building innovative solutions with modern technology",
        "profile_image": "/assets/img/daniel-blackburn.jpg",
        "email": "daniel@blackburnsystems.com",
        "phone": "+1 (555) 123-4567",
        "vcard": "Daniel Blackburn.vcf",
        "resume_url": "https://linkedin.com/in/danielblackburn",
        "resume_download": "Daniel_Blackburn_Resume.pdf",
        "github": "@blackburnd",
        "twitter": "@danielblackburn",
        "skills": [
            "Python", "FastAPI", "GraphQL", "PostgreSQL", "CI/CD", 
            "Cloud Computing", "JavaScript", "React", "Docker"
        ]
    }
    
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
    
    await database.execute(query, {
        **portfolio_data,
        "skills": json.dumps(portfolio_data["skills"]),
        "portfolio_id": portfolio_id
    })
    
    print(f"   ✅ Updated portfolio record for {portfolio_data['name']}")


async def add_work_experience(portfolio_id: str):
    """Add work experience data"""
    print("💼 Adding work experience...")
    
    # Clear existing work experience
    await database.execute(
        "DELETE FROM work_experience WHERE portfolio_id = :portfolio_id",
        {"portfolio_id": portfolio_id}
    )
    
    work_experiences = [
        {
            "company": "Blackburn Systems",
            "position": "Senior Software Developer & Cloud Engineer",
            "location": "Remote",
            "start_date": "2023",
            "end_date": None,
            "description": "Leading development of cloud-native applications and automated deployment pipelines. Specializing in FastAPI, GraphQL, and PostgreSQL solutions with comprehensive CI/CD integration.",
            "is_current": True,
            "company_url": "https://www.blackburnsystems.com",
            "sort_order": 1
        },
        {
            "company": "Previous Technology Company",
            "position": "Full Stack Developer",
            "location": "City, State",
            "start_date": "2020",
            "end_date": "2023",
            "description": "Developed and maintained web applications using modern frameworks. Collaborated with cross-functional teams to deliver high-quality software solutions.",
            "is_current": False,
            "company_url": None,
            "sort_order": 2
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
        
        await database.execute(query, {
            **work,
            "portfolio_id": portfolio_id
        })
        
        print(f"   ✅ Added: {work['position']} at {work['company']}")


async def add_projects(portfolio_id: str):
    """Add projects data"""
    print("🚀 Adding projects...")
    
    # Clear existing projects
    await database.execute(
        "DELETE FROM projects WHERE portfolio_id = :portfolio_id",
        {"portfolio_id": portfolio_id}
    )
    
    projects = [
        {
            "title": "Portfolio Website & API",
            "description": "Modern portfolio website built with FastAPI and GraphQL. Features dynamic content management, OAuth integration, and responsive design with comprehensive admin interface.",
            "url": "https://www.blackburnsystems.com",
            "image_url": "/assets/img/portfolio-project.jpg",
            "technologies": [
                "FastAPI", "GraphQL", "PostgreSQL", "HTML/CSS", "JavaScript"
            ],
            "sort_order": 1
        },
        {
            "title": "Cloud Infrastructure Automation",
            "description": "Automated cloud infrastructure and deployment pipeline with CI/CD integration. Features include automated testing, deployment orchestration, and comprehensive monitoring.",
            "url": "https://github.com/blackburnd/cloud_automation",
            "image_url": "/assets/img/cloud-project.jpg", 
            "technologies": [
                "Python", "Docker", "CI/CD", "Cloud Computing", "Automation"
            ],
            "sort_order": 2
        },
        {
            "title": "Data Analytics Platform",
            "description": "Full-stack data analytics platform with real-time visualization and automated reporting. Built with modern technologies for scalable data processing.",
            "url": None,
            "image_url": "/assets/img/analytics-project.jpg",
            "technologies": [
                "Python", "React", "PostgreSQL", "Data Visualization", "APIs"
            ],
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
        
        await database.execute(query, {
            **project,
            "technologies": json.dumps(project["technologies"]),
            "portfolio_id": portfolio_id
        })
        
        print(f"   ✅ Added: {project['title']}")


async def add_site_config():
    """Add site configuration data extracted from templates"""
    print("⚙️  Adding site configuration...")
    
    # Configuration data extracted from templates
    config_data = {
        # Personal Information
        "full_name": "Daniel Blackburn",
        "professional_title": "Software Developer & Cloud Engineer",
        "email": "daniel@blackburnsystems.com",
        "phone": "+1 (555) 123-4567",
        "location": "Remote",
        "bio": "Passionate software developer with expertise in cloud technologies, automation, and modern web development.",
        "tagline": "Building innovative solutions with modern technology",
        "linkedin_url": "https://linkedin.com/in/danielblackburn",
        "github_url": "https://github.com/blackburnd",
        
        # Site Settings
        "site_title": "Daniel Blackburn - Software Developer & Cloud Engineer",
        "site_description": "Portfolio of Daniel Blackburn, Software Developer & Cloud Engineer specializing in cloud technologies and modern web development.",
        "company_name": "Blackburn Systems",
        "copyright_text": "© 2025 Daniel Blackburn. All rights reserved.",
        "favicon_url": "/favicon.ico",
        "logo_url": "/assets/img/logo.png",
        
        # Navigation
        "nav_home_label": "Home",
        "nav_work_label": "Work",
        "nav_projects_label": "Projects", 
        "nav_contact_label": "Contact",
        "nav_admin_label": "Admin",
        
        # Contact
        "contact_form_enabled": "true",
        "contact_form_title": "Get In Touch",
        "contact_form_subtitle": "Let's discuss your next project",
        "contact_email_subject": "Portfolio Contact Form",
        "contact_success_message": "Thank you for your message! I'll get back to you soon.",
        
        # Social
        "social_linkedin": "https://linkedin.com/in/danielblackburn",
        "social_github": "https://github.com/blackburnd",
        "social_twitter": "https://twitter.com/danielblackburn",
        "social_email": "daniel@blackburnsystems.com",
        
        # Content
        "home_hero_title": "Software Developer & Cloud Engineer",
        "home_hero_subtitle": "Building innovative solutions with modern technology",
        "work_page_title": "Work Experience",
        "work_page_subtitle": "Professional experience and career highlights",
        "projects_page_title": "Featured Projects",
        "projects_page_subtitle": "Selected work and personal projects",
        "contact_page_title": "Get In Touch",
        "contact_page_subtitle": "Let's discuss your next project"
    }
    
    for key, value in config_data.items():
        await SiteConfigManager.set_config(
            key, 
            value, 
            f"Migrated from HTML templates - {key}"
        )
        
    print(f"   ✅ Added {len(config_data)} configuration items")


if __name__ == "__main__":
    asyncio.run(populate_portfolio_data())
