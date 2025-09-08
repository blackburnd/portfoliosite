#!/usr/bin/env python3
"""
Migration script to move LinkedIn OAuth configuration from linkedin_oauth_config 
table to the unified oauth_apps table.
"""

import asyncio
import sys
from database import database

async def migrate_linkedin_oauth():
    """Migrate LinkedIn OAuth configuration to oauth_apps table"""
    
    try:
        await database.connect()
        
        # Check if linkedin_oauth_config table exists and has data
        check_query = """
            SELECT COUNT(*) as count 
            FROM information_schema.tables 
            WHERE table_name = 'linkedin_oauth_config' AND table_schema = 'public'
        """
        table_exists = await database.fetch_one(check_query)
        
        if not table_exists['count']:
            print("✅ linkedin_oauth_config table doesn't exist - no migration needed")
            return
        
        # Get existing LinkedIn OAuth configurations
        linkedin_configs_query = """
            SELECT app_name, client_id, client_secret, redirect_uri, 
                   configured_by_email, created_at, updated_at, is_active
            FROM linkedin_oauth_config 
            WHERE is_active = true
        """
        
        linkedin_configs = await database.fetch_all(linkedin_configs_query)
        
        if not linkedin_configs:
            print("✅ No active LinkedIn OAuth configurations to migrate")
            return
            
        print(f"📦 Found {len(linkedin_configs)} LinkedIn OAuth configurations to migrate")
        
        # Migrate each configuration to oauth_apps table
        migrated = 0
        for config in linkedin_configs:
            try:
                # Insert into oauth_apps table
                insert_query = """
                    INSERT INTO oauth_apps (
                        provider, app_name, client_id, client_secret, redirect_uri, 
                        scopes, encryption_key, created_by, created_at, updated_at, is_active
                    )
                    VALUES (
                        'linkedin', :app_name, :client_id, :client_secret, :redirect_uri,
                        ARRAY['r_liteprofile', 'r_emailaddress'], 'oauth_key', 
                        :created_by, :created_at, :updated_at, :is_active
                    )
                    ON CONFLICT (provider, app_name) DO NOTHING
                """
                
                await database.execute(insert_query, {
                    "app_name": config["app_name"],
                    "client_id": config["client_id"],
                    "client_secret": config["client_secret"],
                    "redirect_uri": config["redirect_uri"],
                    "created_by": config["configured_by_email"],
                    "created_at": config["created_at"],
                    "updated_at": config["updated_at"],
                    "is_active": config["is_active"]
                })
                
                migrated += 1
                print(f"✅ Migrated LinkedIn OAuth app: {config['app_name']}")
                
            except Exception as e:
                print(f"❌ Failed to migrate config {config['app_name']}: {e}")
        
        print(f"🎉 Migration complete! Migrated {migrated} LinkedIn OAuth configurations")
        
        # Optionally deactivate the old configurations
        if migrated > 0:
            deactivate_query = "UPDATE linkedin_oauth_config SET is_active = false WHERE is_active = true"
            await database.execute(deactivate_query)
            print("🔒 Deactivated old LinkedIn OAuth configurations in linkedin_oauth_config table")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        sys.exit(1)
    
    finally:
        await database.disconnect()

if __name__ == "__main__":
    print("🚀 Starting LinkedIn OAuth migration to oauth_apps table...")
    asyncio.run(migrate_linkedin_oauth())
    print("✅ Migration script completed")
