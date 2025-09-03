#!/usr/bin/env python3
import asyncio
import asyncpg
import os

async def apply_oauth_schema():
    """Apply the OAuth management schema to the database"""
    
    # Get database connection details from environment variables
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL environment variable not set")
        return
    
    # Parse database URL (format: postgresql://user:pass@host:port/db)
    try:
        import urllib.parse
        parsed = urllib.parse.urlparse(database_url)
        host = parsed.hostname
        port = parsed.port
        database = parsed.path.lstrip('/')
        user = parsed.username
        password = parsed.password
    
    try:
        # Connect to database
        conn = await asyncpg.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password
        )
        
        print(f"✅ Connected to PostgreSQL database: {database}")
        
        # Read the OAuth management schema
        schema_file = "sql/oauth_management_schema.sql"
        if os.path.exists(schema_file):
            with open(schema_file, 'r') as f:
                schema_sql = f.read()
            
            print(f"📖 Reading schema from {schema_file}")
            
            # Split the schema into individual statements
            statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip()]
            
            for stmt in statements:
                try:
                    await conn.execute(stmt)
                    print(f"✅ Executed: {stmt[:50]}...")
                except Exception as e:
                    if "already exists" in str(e):
                        print(f"⚠️  Already exists: {stmt[:50]}...")
                    else:
                        print(f"❌ Error executing: {stmt[:50]}...")
                        print(f"   Error: {e}")
            
            print("✅ OAuth management schema applied successfully")
            
        else:
            print(f"❌ Schema file not found: {schema_file}")
            
        # Check existing OAuth configurations
        query = "SELECT id, app_name, client_id, created_at FROM oauth_apps ORDER BY created_at"
        try:
            rows = await conn.fetch(query)
            print(f"\n📋 Current OAuth apps in database:")
            for row in rows:
                print(f"   - {row['app_name']} (ID: {row['id'][:8]}..., Client: {row['client_id']})")
        except Exception as e:
            print(f"⚠️  Could not query oauth_apps table: {e}")
            
        # Check LinkedIn OAuth config table
        linkedin_query = "SELECT app_name, client_id, is_configured FROM linkedin_oauth_config"
        try:
            rows = await conn.fetch(linkedin_query)
            print(f"\n📋 LinkedIn OAuth configurations:")
            for row in rows:
                print(f"   - {row['app_name']}: {row['client_id']} (Configured: {row['is_configured']})")
        except Exception as e:
            print(f"⚠️  Could not query linkedin_oauth_config table: {e}")
        
        await conn.close()
        print("🔒 Database connection closed")
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    asyncio.run(apply_oauth_schema())
