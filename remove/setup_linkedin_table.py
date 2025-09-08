#!/usr/bin/env python3
import asyncio
import asyncpg

async def setup_linkedin_oauth_table():
    """Create the linkedin_oauth_config table directly"""
    
    try:
        # Connect to database with known credentials
        conn = await asyncpg.connect(
            host="35.184.209.128",
            port=5432,
            database="daniel_portfolio",
            user="postgres",
            password="-8JB6On1kTf6puF-"
        )
        
        print("✅ Connected to PostgreSQL database")
        
        # Create the linkedin_oauth_config table
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
        
        await conn.execute(create_table_sql)
        print("✅ linkedin_oauth_config table created")
        
        # Check existing data
        count = await conn.fetchval("SELECT COUNT(*) FROM linkedin_oauth_config")
        print(f"📊 Current records in linkedin_oauth_config: {count}")
        
        if count > 0:
            # Show existing records
            records = await conn.fetch("SELECT app_name, client_id, is_active FROM linkedin_oauth_config")
            for record in records:
                print(f"  - {record['app_name']}: {record['client_id']} (Active: {record['is_active']})")
        
        await conn.close()
        print("🔒 Database connection closed")
        return True
        
    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(setup_linkedin_oauth_table())
    if success:
        print("✅ LinkedIn OAuth table setup completed")
    else:
        print("❌ LinkedIn OAuth table setup failed")
