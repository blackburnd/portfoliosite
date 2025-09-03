#!/usr/bin/env python3
"""
Quick script to check LinkedIn OAuth configuration in the database
"""
import asyncio
import os
from databases import Database

# Database configuration - connect to postgres db first to check what exists
DATABASE_URL = "postgresql://postgres:-8JB6On1kTf6puF-@35.184.209.128:5432/postgres"

async def check_linkedin_config():
    """Check if LinkedIn OAuth configuration exists"""
    database = Database(DATABASE_URL)
    
    try:
        await database.connect()
        print("✓ Connected to database successfully")
        
        # First, check what databases exist
        db_query = "SELECT datname FROM pg_database WHERE datistemplate = false;"
        databases = await database.fetch_all(db_query)
        print("Available databases:")
        for db in databases:
            print(f"  - {db['datname']}")
        
        # Check if portfolio database exists
        portfolio_exists = any(db['datname'] == 'daniel_portfolio' for db in databases)
        if not portfolio_exists:
            print("Daniel portfolio database does not exist. Creating it...")
            await database.execute("CREATE DATABASE daniel_portfolio;")
            print("✓ Created daniel_portfolio database")
        
        # Now disconnect and reconnect to portfolio database
        await database.disconnect()
        
        # Connect to daniel_portfolio database
        portfolio_url = "postgresql://postgres:-8JB6On1kTf6puF-@35.184.209.128:5432/daniel_portfolio"
        database = Database(portfolio_url)
        await database.connect()
        print("✓ Connected to daniel_portfolio database")
        
        # Check if linkedin_oauth_config table exists
        table_check = """
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'linkedin_oauth_config'
        );
        """
        
        table_exists = await database.fetch_val(table_check)
        print(f"LinkedIn OAuth config table exists: {table_exists}")
        
        if table_exists:
            # Check current configuration
            config_query = "SELECT * FROM linkedin_oauth_config LIMIT 1;"
            config = await database.fetch_one(config_query)
            
            if config:
                print("Current LinkedIn OAuth config found:")
                for key, value in config.items():
                    if 'secret' in key.lower():
                        print(f"  {key}: {'*' * len(str(value)) if value else 'None'}")
                    else:
                        print(f"  {key}: {value}")
            else:
                print("No LinkedIn OAuth configuration found in table")
        else:
            print("LinkedIn OAuth config table does not exist")
            
            # Check if we can create it
            create_table = """
            CREATE TABLE IF NOT EXISTS linkedin_oauth_config (
                id SERIAL PRIMARY KEY,
                client_id VARCHAR(255) NOT NULL,
                client_secret VARCHAR(255) NOT NULL,
                redirect_uri VARCHAR(255) NOT NULL,
                scopes VARCHAR(255) DEFAULT 'r_liteprofile,r_emailaddress',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
            
            await database.execute(create_table)
            print("✓ Created linkedin_oauth_config table")
        
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        print("Check if:")
        print("1. Database credentials are correct")
        print("2. Database server is accessible")
        print("3. Network connection is working")
    
    finally:
        await database.disconnect()

if __name__ == "__main__":
    asyncio.run(check_linkedin_config())
