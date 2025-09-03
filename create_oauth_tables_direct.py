#!/usr/bin/env python3
import asyncio
import asyncpg

async def create_oauth_tables():
    """Create OAuth tables in production database"""
    
    # Production database connection
    conn = await asyncpg.connect(
        host="35.184.209.128",
        port=5432,
        database="daniel_portfolio",
        user="postgres",
        password="-8JB6On1kTf6puF-"
    )
    
    print("✅ Connected to production database")
    
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
    
    try:
        # Execute table creation
        await conn.execute(oauth_system_settings_sql)
        print("✅ Created oauth_system_settings table")
        
        await conn.execute(oauth_apps_sql)
        print("✅ Created oauth_apps table")
        
        await conn.execute(linkedin_oauth_config_sql)
        print("✅ Created linkedin_oauth_config table")
        
        # Insert default encryption key
        insert_key_sql = """
        INSERT INTO oauth_system_settings (setting_key, setting_value, description, is_encrypted, created_by)
        VALUES ('master_encryption_key', 'TEMP_GENERATED_KEY_REPLACE_IN_PRODUCTION', 'Master key for encrypting OAuth secrets', false, 'system')
        ON CONFLICT (setting_key) DO NOTHING;
        """
        await conn.execute(insert_key_sql)
        print("✅ Inserted default encryption key")
        
        print("🎉 All OAuth tables created successfully!")
        
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
    finally:
        await conn.close()
        print("🔒 Database connection closed")

if __name__ == "__main__":
    asyncio.run(create_oauth_tables())
