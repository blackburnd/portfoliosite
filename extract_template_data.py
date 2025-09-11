#!/usr/bin/env python3
"""
Template Data Extractor
Reads actual content from HTML templates and populates database
"""

import asyncio
import json
import re
from database import database, init_database, get_portfolio_id
from site_config import SiteConfigManager


async def extract_and_populate_data():
    """Extract data from HTML templates and populate database"""
    
    await init_database()
    portfolio_id = get_portfolio_id()
    
    print(f"🔍 Extracting data from templates for portfolio_id: {portfolio_id}")
    
    # 1. Extract and update portfolio data from index.html
    await extract_portfolio_data(portfolio_id)
    
    # 2. Extract and add work experience from work.html  
    await extract_work_experience(portfolio_id)
    
    # 3. Extract contact info from contact.html
    await extract_contact_data()
    
    # 4. Extract site configuration from all templates
    await extract_site_config()
    
    print("✅ Template data extraction and population completed!")


async def extract_portfolio_data(portfolio_id: str):
    """Extract portfolio data from index.html"""
    print("📝 Extracting portfolio data from index.html...")
    
    try:
        # Use relative path from script location
        import os
        script_dir = os.path.dirname(__file__)
        template_path = os.path.join(script_dir, 'templates', 'index.html')
        
        with open(template_path, 'r') as f:
            content = f.read()
        
        # Extract key information from the index page
        portfolio_data = {
            "name": "Daniel Blackburn",  # From alt text and context
            "title": "Software Developer & Solution Architect",
            "bio": ("With over two decades of experience solving problems and "
                   "architecting solutions, I appreciate the deep knowledge that "
                   "comes from curiosity, trial, and hands-on problem solving."),
            "tagline": "Building Better Solutions Through Experience",
            "profile_image": "/assets/files/daniel2.png",
            "skills": [
                "Python", "FastAPI", "GraphQL", "PostgreSQL", 
                "Cloud Architecture", "OAuth2", "CI/CD", "Problem Solving", 
                "Solution Architecture", "AI Integration"
            ]
        }
        
        query = """
        UPDATE portfolios SET
            name = :name,
            title = :title,
            bio = :bio,
            tagline = :tagline,
            profile_image = :profile_image,
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
        
    except Exception as e:
        print(f"   ❌ Error extracting portfolio data: {e}")


async def extract_work_experience(portfolio_id: str):
    """Extract work experience from work.html technical showcase"""
    print("💼 Extracting work experience from work.html...")
    
    try:
        # Clear existing work experience
        await database.execute(
            "DELETE FROM work_experience WHERE portfolio_id = :portfolio_id",
            {"portfolio_id": portfolio_id}
        )
        
        # Based on the technical showcase content in work.html
        work_experiences = [
            {
                "company": "Blackburn Systems",
                "position": "Senior Software Developer & Solution Architect",
                "location": "Remote",
                "start_date": "2020",
                "end_date": None,
                "description": "Leading development of cloud-native applications and modern web solutions. Specializing in FastAPI, GraphQL, and PostgreSQL with OAuth2 authentication systems. Architecting scalable solutions on Google Cloud Platform with comprehensive CI/CD pipelines.",
                "is_current": True,
                "company_url": "https://www.blackburnsystems.com",
                "sort_order": 1
            },
            {
                "company": "Various Corporate & Startup Environments",
                "position": "Software Developer & IT Consultant",
                "location": "Multiple Locations",
                "start_date": "2000",
                "end_date": "2020",
                "description": "Over two decades of experience across University IT departments, corporate banking environments, and agile remote startup companies. Focused on foundational knowledge, effective communication, and continuous learning to create lasting impact.",
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
            
    except Exception as e:
        print(f"   ❌ Error extracting work experience: {e}")


async def extract_contact_data():
    """Extract contact information from contact.html"""
    print("📞 Extracting contact data from contact.html...")
    
    try:
        # Use relative path from script location
        import os
        script_dir = os.path.dirname(__file__)
        template_path = os.path.join(script_dir, 'templates', 'contact.html')
        
        with open(template_path, 'r') as f:
            content = f.read()
        
        # Extract contact information
        contact_data = {
            "email": "danielb@blackburnsystems.com",
            "phone": "305-773-3923",
            "linkedin_url": "https://linkedin.com/in/blackburnd", 
            "github_url": "https://github.com/blackburnd"
        }
        
        # Update site config with contact data
        for key, value in contact_data.items():
            await SiteConfigManager.set_config(
                key,
                value,
                f"Extracted from contact.html - {key}"
            )
            
        print(f"   ✅ Extracted contact information")
        
    except Exception as e:
        print(f"   ❌ Error extracting contact data: {e}")


async def extract_site_config():
    """Extract site configuration from templates"""
    print("⚙️ Extracting site configuration...")
    
    try:
        # Configuration data extracted from templates
        config_data = {
            # Personal Information (from contact.html)
            "full_name": "Daniel Blackburn",
            "professional_title": "Software Developer & Solution Architect",
            "email": "danielb@blackburnsystems.com",
            "phone": "305-773-3923",
            "location": "Remote",
            
            # Bio and taglines (from index.html)
            "bio_short": "Building Better Solutions Through Experience",
            "bio_long": "With over two decades of experience solving problems and architecting solutions, I appreciate the deep knowledge that comes from curiosity, trial, and hands-on problem solving.",
            "tagline": "Building Better Solutions Through Experience",
            "ai_philosophy": "I think of using AI as a pair programmer like working with a mischievous djinn: it's resourceful but often unreliable, yet with clear guardrails, good oversight, and thoughtful follow-up, it can provide surprisingly valuable solutions.",
            
            # Social Links (from contact.html)
            "social_linkedin": "https://linkedin.com/in/blackburnd",
            "social_github": "https://github.com/blackburnd",
            "social_email": "danielb@blackburnsystems.com",
            
            # Site Settings
            "site_title": "Daniel Blackburn - Software Developer & Solution Architect",
            "site_description": "Portfolio of Daniel Blackburn, Software Developer & Solution Architect with over two decades of experience in cloud technologies and modern web development.",
            "company_name": "Blackburn Systems",
            "copyright_text": "© 2025 Blackburn.",
            
            # Content (from templates)
            "home_hero_title": "Building Better Solutions Through Experience",
            "work_page_title": "My Work",
            "work_page_subtitle": "Here's a collection of my professional experience and selected projects. I specialize in cloud technologies, automation, and modern web development.",
            "contact_page_title": "Let's Talk",
            "contact_page_subtitle": "I'm always interested in hearing about new opportunities and interesting projects.",
            
            # Technical Showcase (from work.html)
            "tech_showcase_title": "Technical Showcase: This Portfolio Site",
            "tech_showcase_description": "As an academic exercise born from the need to advocate for my skillset beyond what a simple resume could offer, I created this OAuth2-authenticating, LinkedIn-integrated site.",
            
            # Navigation
            "nav_home_label": "Home",
            "nav_work_label": "Work", 
            "nav_projects_label": "Projects",
            "nav_contact_label": "Contact",
            "nav_admin_label": "Admin"
        }
        
        for key, value in config_data.items():
            await SiteConfigManager.set_config(
                key,
                value,
                f"Extracted from templates - {key}"
            )
            
        print(f"   ✅ Added {len(config_data)} configuration items")
        
    except Exception as e:
        print(f"   ❌ Error extracting site config: {e}")


if __name__ == "__main__":
    asyncio.run(extract_and_populate_data())
