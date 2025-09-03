#!/usr/bin/env python3
"""
Create OAuth management tables using existing database connection
"""
import sys
import os
import asyncio

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import database from main application
from database import database
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def create_oauth_tables():
    """Create OAuth management tables"""
    try:
        # Connect to database
        await database.connect()
        logger.info("✅ Connected to database")
        
        # Create oauth_system_settings table
        oauth_system_settings_sql = """
        CREATE TABLE IF NOT EXISTS oauth_system_settings (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            setting_key VARCHAR(100) UNIQUE NOT NULL,
            setting_value TEXT NOT NULL,
            description TEXT,
            is_encrypted BOOLEAN DEFAULT false,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            created_by VARCHAR(255) NOT NULL
        );
        """
        
        await database.execute(oauth_system_settings_sql)
        logger.info("✅ Created oauth_system_settings table")
        
        # Create oauth_apps table
        oauth_apps_sql = """
        CREATE TABLE IF NOT EXISTS oauth_apps (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            provider VARCHAR(50) NOT NULL,
            app_name VARCHAR(255) NOT NULL,
            client_id VARCHAR(255) NOT NULL,
            client_secret TEXT NOT NULL,
            redirect_uri VARCHAR(500) NOT NULL,
            scopes TEXT[],
            is_active BOOLEAN DEFAULT true,
            encryption_key TEXT NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            created_by VARCHAR(255) NOT NULL,
            UNIQUE(provider, app_name)
        );
        """
        
        await database.execute(oauth_apps_sql)
        logger.info("✅ Created oauth_apps table")
        
        # Create linkedin_oauth_config table
        linkedin_oauth_config_sql = """
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
        
        await database.execute(linkedin_oauth_config_sql)
        logger.info("✅ Created linkedin_oauth_config table")
        
        # Create updated_at trigger function
        trigger_function_sql = """
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ language 'plpgsql';
        """
        
        await database.execute(trigger_function_sql)
        logger.info("✅ Created update trigger function")
        
        # Create triggers
        oauth_system_settings_trigger_sql = """
        CREATE OR REPLACE TRIGGER update_oauth_system_settings_updated_at 
            BEFORE UPDATE ON oauth_system_settings 
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        """
        
        await database.execute(oauth_system_settings_trigger_sql)
        logger.info("✅ Created oauth_system_settings trigger")
        
        oauth_apps_trigger_sql = """
        CREATE OR REPLACE TRIGGER update_oauth_apps_updated_at 
            BEFORE UPDATE ON oauth_apps 
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        """
        
        await database.execute(oauth_apps_trigger_sql)
        logger.info("✅ Created oauth_apps trigger")
        
        # Check tables were created
        check_query = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('oauth_system_settings', 'oauth_apps', 'linkedin_oauth_config')
        """
        
        tables = await database.fetch_all(check_query)
        existing_tables = [table['table_name'] for table in tables]
        logger.info(f"📋 Created OAuth tables: {existing_tables}")
        
        await database.disconnect()
        logger.info("🔒 Database connection closed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to create OAuth tables: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(create_oauth_tables())
    if result:
        print("✅ OAuth tables created successfully")
    else:
        print("❌ Failed to create OAuth tables")
        sys.exit(1)
