#!/usr/bin/env python3
"""
Simple database schema check using existing main.py database connection
"""
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import database from main application
from database import database
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def check_database_schema():
    """Check if required tables exist in the database"""
    try:
        # Connect to database
        await database.connect()
        logger.info("✅ Connected to database")
        
        # Check if linkedin_oauth_config table exists
        check_query = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('linkedin_oauth_config', 'oauth_apps', 'oauth_system_settings')
        """
        
        tables = await database.fetch_all(check_query)
        existing_tables = [table['table_name'] for table in tables]
        
        logger.info(f"📋 Existing OAuth tables: {existing_tables}")
        
        # Check linkedin_oauth_config table structure if it exists
        if 'linkedin_oauth_config' in existing_tables:
            columns_query = """
                SELECT column_name, data_type, is_nullable 
                FROM information_schema.columns 
                WHERE table_name = 'linkedin_oauth_config'
                ORDER BY ordinal_position
            """
            columns = await database.fetch_all(columns_query)
            logger.info("📊 linkedin_oauth_config columns:")
            for col in columns:
                logger.info(f"  - {col['column_name']}: {col['data_type']} ({'NULL' if col['is_nullable'] == 'YES' else 'NOT NULL'})")
        else:
            logger.warning("❌ linkedin_oauth_config table does not exist")
            
        # Try to create the missing table
        logger.info("🔧 Creating linkedin_oauth_config table if missing...")
        create_table_sql = """
            CREATE TABLE IF NOT EXISTS linkedin_oauth_config (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                app_name VARCHAR(200) NOT NULL DEFAULT 'Portfolio LinkedIn Integration',
                client_id VARCHAR(200) NOT NULL,
                client_secret TEXT NOT NULL,
                redirect_uri VARCHAR(500) NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                configured_by_email VARCHAR(100) NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
        """
        
        await database.execute(create_table_sql)
        logger.info("✅ linkedin_oauth_config table created/verified")
        
        # Check if table has any data
        count_query = "SELECT COUNT(*) as count FROM linkedin_oauth_config"
        count_result = await database.fetch_one(count_query)
        logger.info(f"📊 linkedin_oauth_config records: {count_result['count']}")
        
        await database.disconnect()
        logger.info("🔒 Database connection closed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Database check failed: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(check_database_schema())
    if result:
        print("✅ Database schema check completed successfully")
    else:
        print("❌ Database schema check failed")
        sys.exit(1)
