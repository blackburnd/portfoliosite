#!/usr/bin/env python3
"""
Debug script to check OAuth apps table contents
"""
import asyncio
import os
from database import database

async def debug_oauth_table():
    """Check what's in the oauth_apps table"""
    try:
        # Connect to database
        await database.connect()
        
        # Check all oauth_apps records
        query = """
            SELECT provider, app_name, client_id, client_secret, redirect_uri, scopes, created_at, updated_at
            FROM oauth_apps
            ORDER BY provider, updated_at DESC
        """
        results = await database.fetch_all(query)
        
        print("=== OAuth Apps Table Contents ===")
        if not results:
            print("❌ No records found in oauth_apps table")
        else:
            for row in results:
                print(f"\n📱 Provider: {row['provider']}")
                print(f"   App Name: '{row['app_name']}'")
                print(f"   Client ID: '{row['client_id']}'")
                print(f"   Client Secret: '{row['client_secret']}'")
                print(f"   Redirect URI: '{row['redirect_uri']}'")
                print(f"   Scopes: '{row['scopes']}'")
                print(f"   Created: {row['created_at']}")
                print(f"   Updated: {row['updated_at']}")
                
                # Check for NULL vs empty string
                for field in ['app_name', 'client_id', 'client_secret', 'redirect_uri', 'scopes']:
                    value = row[field]
                    if value is None:
                        print(f"   ⚠️  {field} is NULL")
                    elif value == "":
                        print(f"   ⚠️  {field} is empty string")
        
        # Also check the table structure
        print("\n=== OAuth Apps Table Structure ===")
        structure_query = """
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = 'oauth_apps'
            ORDER BY ordinal_position
        """
        columns = await database.fetch_all(structure_query)
        for col in columns:
            print(f"{col['column_name']}: {col['data_type']} (nullable: {col['is_nullable']}, default: {col['column_default']})")
            
    except Exception as e:
        print(f"❌ Error checking OAuth table: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await database.disconnect()

if __name__ == "__main__":
    asyncio.run(debug_oauth_table())
