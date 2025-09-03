#!/usr/bin/env python3
"""
Check the actual structure of linkedin_oauth_config table
"""
import asyncio
from databases import Database

DATABASE_URL = "postgresql://postgres:-8JB6On1kTf6puF-@35.184.209.128:5432/daniel_portfolio"

async def check_table_structure():
    """Check the actual table structure"""
    database = Database(DATABASE_URL)
    
    try:
        await database.connect()
        print("✓ Connected to daniel_portfolio database")
        
        # Get table structure
        structure_query = """
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns 
        WHERE table_name = 'linkedin_oauth_config'
        ORDER BY ordinal_position;
        """
        
        columns = await database.fetch_all(structure_query)
        print("\nlinkedin_oauth_config table structure:")
        for col in columns:
            print(f"  {col['column_name']}: {col['data_type']} {'NULL' if col['is_nullable'] == 'YES' else 'NOT NULL'}")
        
    except Exception as e:
        print(f"✗ Error: {e}")
    
    finally:
        await database.disconnect()

if __name__ == "__main__":
    asyncio.run(check_table_structure())
