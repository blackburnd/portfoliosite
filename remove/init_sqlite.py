#!/usr/bin/env python3
"""
Initialize SQLite database with the portfolio schema and sample data.
This adapts the PostgreSQL schema for SQLite compatibility.
"""

import sqlite3
import json
import uuid
from datetime import datetime

def init_sqlite_db(db_path="test.db"):
    """Initialize SQLite database with schema and sample data."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Enable foreign key support
    cursor.execute("PRAGMA foreign_keys = ON")
    
    # Create portfolios table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS portfolios (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            title TEXT NOT NULL,
            bio TEXT NOT NULL,
            tagline TEXT,
            profile_image TEXT,
            email TEXT NOT NULL,
            phone TEXT,
            vcard TEXT,
            resume_url TEXT,
            resume_download TEXT,
            github TEXT,
            twitter TEXT,
            skills TEXT DEFAULT '[]',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create work_experience table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS work_experience (
            id TEXT PRIMARY KEY,
            portfolio_id TEXT NOT NULL,
            company TEXT NOT NULL,
            position TEXT NOT NULL,
            location TEXT,
            start_date TEXT NOT NULL,
            end_date TEXT,
            description TEXT,
            is_current BOOLEAN DEFAULT 0,
            company_url TEXT,
            sort_order INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (portfolio_id) REFERENCES portfolios(id) ON DELETE CASCADE
        )
    """)
    
    # Create projects table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            portfolio_id TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            url TEXT,
            image_url TEXT,
            technologies TEXT DEFAULT '[]',
            sort_order INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (portfolio_id) REFERENCES portfolios(id) ON DELETE CASCADE
        )
    """)
    
    # Create contact_messages table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS contact_messages (
            id TEXT PRIMARY KEY,
            portfolio_id TEXT NOT NULL,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            subject TEXT,
            message TEXT NOT NULL,
            is_read BOOLEAN DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (portfolio_id) REFERENCES portfolios(id) ON DELETE CASCADE
        )
    """)
    
    # Create linkedin_oauth_credentials table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS linkedin_oauth_credentials (
            id TEXT PRIMARY KEY,
            admin_email TEXT NOT NULL UNIQUE,
            access_token TEXT NOT NULL,
            refresh_token TEXT,
            token_expires_at TEXT,
            linkedin_profile_id TEXT,
            scope TEXT DEFAULT 'r_liteprofile,r_emailaddress',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_work_experience_portfolio_id ON work_experience(portfolio_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_work_experience_sort_order ON work_experience(sort_order)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_projects_portfolio_id ON projects(portfolio_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_projects_sort_order ON projects(sort_order)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_contact_messages_portfolio_id ON contact_messages(portfolio_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_contact_messages_is_read ON contact_messages(is_read)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_linkedin_oauth_admin_email ON linkedin_oauth_credentials(admin_email)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_linkedin_oauth_expires_at ON linkedin_oauth_credentials(token_expires_at)")
    
    # Insert initial portfolio data
    portfolio_skills = json.dumps([
        "Python", "FastAPI", "GraphQL", "PostgreSQL", "CI/CD", "Cloud Computing", 
        "JavaScript", "React", "Docker", "SQLite"
    ])
    
    cursor.execute("""
        INSERT OR REPLACE INTO portfolios (
            id, name, title, bio, tagline, profile_image,
            email, phone, vcard, resume_url, resume_download, github, twitter, skills
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        'daniel-blackburn',
        'Daniel Blackburn',
        'Software Developer & Cloud Engineer',
        'Passionate software developer with expertise in cloud technologies, automation, and modern web development. Experienced in building scalable applications and robust CI/CD pipelines.',
        'Building innovative solutions with modern technology',
        '/assets/files/daniel1.jpg',
        'daniel@blackburnsystems.com',
        '555-123-4567',
        '/assets/files/danielblackburn.vcf',
        '/resume/',
        '/assets/files/danielblackburn.pdf',
        '@blackburnd',
        '@danielblackburn',
        portfolio_skills
    ))
    
    # Insert sample work experience
    work_items = [
        {
            'id': str(uuid.uuid4()),
            'portfolio_id': 'daniel-blackburn',
            'company': 'Blackburn Systems',
            'position': 'Software Engineer/Developer',
            'location': 'Remote',
            'start_date': '2023',
            'end_date': None,
            'description': 'Building innovative solutions with modern technologies including FastAPI, GraphQL, and cloud infrastructure. Leading development of automated deployment pipelines and scalable web applications.',
            'is_current': True,
            'company_url': 'https://blackburnsystems.com',
            'sort_order': 1
        },
        {
            'id': str(uuid.uuid4()),
            'portfolio_id': 'daniel-blackburn',
            'company': 'Previous Company',
            'position': 'Senior Developer',
            'location': 'Remote',
            'start_date': '2021',
            'end_date': '2023',
            'description': 'Developed and maintained web applications using modern frameworks. Collaborated with cross-functional teams to deliver high-quality software solutions.',
            'is_current': False,
            'company_url': None,
            'sort_order': 2
        }
    ]
    
    for work in work_items:
        cursor.execute("""
            INSERT OR REPLACE INTO work_experience (
                id, portfolio_id, company, position, location, start_date, end_date,
                description, is_current, company_url, sort_order
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            work['id'], work['portfolio_id'], work['company'], work['position'],
            work['location'], work['start_date'], work['end_date'], work['description'],
            work['is_current'], work['company_url'], work['sort_order']
        ))
    
    # Insert sample projects
    project_items = [
        {
            'id': str(uuid.uuid4()),
            'portfolio_id': 'daniel-blackburn',
            'title': 'Cloud Infrastructure Automation',
            'description': 'Automated cloud infrastructure and deployment pipeline with CI/CD integration. Features include automated testing, deployment orchestration, and monitoring.',
            'url': 'https://github.com/blackburnd/cloud_machine_repo',
            'technologies': json.dumps(["Python", "FastAPI", "GraphQL", "CI/CD", "PostgreSQL", "Docker"]),
            'sort_order': 1
        },
        {
            'id': str(uuid.uuid4()),
            'portfolio_id': 'daniel-blackburn',
            'title': 'Portfolio API & Website',
            'description': 'Modern portfolio website backend built with FastAPI and GraphQL. Features real-time contact forms, dynamic content management, and responsive design.',
            'url': 'https://blackburnsystems.com',
            'technologies': json.dumps(["FastAPI", "GraphQL", "SQLite", "HTML/CSS", "JavaScript"]),
            'sort_order': 2
        },
        {
            'id': str(uuid.uuid4()),
            'portfolio_id': 'daniel-blackburn',
            'title': 'Machine Learning Pipeline',
            'description': 'End-to-end machine learning pipeline for data processing and model deployment. Includes automated training, validation, and monitoring capabilities.',
            'url': None,
            'technologies': json.dumps(["Python", "ML", "Data Science", "APIs"]),
            'sort_order': 3
        }
    ]
    
    for project in project_items:
        cursor.execute("""
            INSERT OR REPLACE INTO projects (
                id, portfolio_id, title, description, url, technologies, sort_order
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            project['id'], project['portfolio_id'], project['title'],
            project['description'], project['url'], project['technologies'], project['sort_order']
        ))
    
    conn.commit()
    conn.close()
    
    print(f"✅ SQLite database initialized at {db_path}")
    print("📊 Sample data inserted successfully")

if __name__ == "__main__":
    init_sqlite_db()
