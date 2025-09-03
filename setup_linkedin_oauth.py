#!/usr/bin/env python3
"""
Setup LinkedIn OAuth configuration for issue #25
"""
import asyncio
from databases import Database

DATABASE_URL = "postgresql://postgres:-8JB6On1kTf6puF-@35.184.209.128:5432/daniel_portfolio"

async def setup_linkedin_oauth():
    """Setup LinkedIn OAuth configuration in the database"""
    database = Database(DATABASE_URL)
    
    try:
        await database.connect()
        print("✓ Connected to daniel_portfolio database")
        
        # Check if configuration already exists
        check_query = "SELECT COUNT(*) FROM linkedin_oauth_config;"
        count = await database.fetch_val(check_query)
        
        if count > 0:
            print(f"Found {count} existing LinkedIn OAuth configs")
            # Show existing config
            config_query = "SELECT * FROM linkedin_oauth_config LIMIT 1;"
            config = await database.fetch_one(config_query)
            print("Current configuration:")
            for key, value in config.items():
                if 'secret' in key.lower():
                    print(f"  {key}: {'*' * 20}")
                else:
                    print(f"  {key}: {value}")
            
            update = input("Update existing configuration? (y/N): ").lower()
            if update != 'y':
                print("Keeping existing configuration")
                return
            
            # Delete existing config to update
            await database.execute("DELETE FROM linkedin_oauth_config;")
            print("Deleted existing configuration")
        
        # Get LinkedIn OAuth app details
        print("\nTo set up LinkedIn OAuth, you need to:")
        print("1. Go to https://www.linkedin.com/developers/apps")
        print("2. Create a new app or use existing one")
        print("3. Get your Client ID and Client Secret")
        print("4. Set redirect URI to: https://www.blackburnsystems.com/linkedin/oauth/callback")
        print()
        
        app_name = input("Enter App Name [Portfolio LinkedIn]: ").strip()
        if not app_name:
            app_name = "Portfolio LinkedIn"
        
        client_id = input("Enter LinkedIn Client ID: ").strip()
        if not client_id:
            print("Client ID is required!")
            return
            
        client_secret = input("Enter LinkedIn Client Secret: ").strip()
        if not client_secret:
            print("Client Secret is required!")
            return
        
        redirect_uri = input("Enter Redirect URI [https://www.blackburnsystems.com/linkedin/oauth/callback]: ").strip()
        if not redirect_uri:
            redirect_uri = "https://www.blackburnsystems.com/linkedin/oauth/callback"
        
        configured_by = input("Enter your email: ").strip()
        if not configured_by:
            print("Email is required!")
            return
        
        # Insert configuration
        insert_query = """
        INSERT INTO linkedin_oauth_config 
        (app_name, client_id, client_secret, redirect_uri, is_active, configured_by_email)
        VALUES (:app_name, :client_id, :client_secret, :redirect_uri, :is_active, :configured_by_email)
        RETURNING id;
        """
        
        config_id = await database.fetch_val(insert_query, {
            "app_name": app_name,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "is_active": True,
            "configured_by_email": configured_by
        })
        print(f"✓ LinkedIn OAuth configuration created with ID: {config_id}")
        
        print("\nConfiguration summary:")
        print(f"  App Name: {app_name}")
        print(f"  Client ID: {client_id}")
        print(f"  Client Secret: {'*' * 20}")
        print(f"  Redirect URI: {redirect_uri}")
        print(f"  Configured by: {configured_by}")
        print(f"  Active: True")
        
        print("\nNext steps:")
        print("1. Restart your application")
        print("2. Go to /linkedin admin page")
        print("3. Test the 'Connect LinkedIn' button")
        
    except Exception as e:
        print(f"✗ Error: {e}")
    
    finally:
        await database.disconnect()

if __name__ == "__main__":
    asyncio.run(setup_linkedin_oauth())
