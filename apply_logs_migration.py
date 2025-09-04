#!/usr/bin/env python3
"""
Apply the application logs table migration to the database.
"""

import os
import asyncio
import databases


async def apply_logs_migration():
    """Apply the logs table migration"""
    database_url = os.getenv("_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL environment variable not set")
        return False
    
    database = databases.Database(database_url)
    
    try:
        await database.connect()
        print("✅ Connected to database")
        
        # Read the migration SQL
        migration_path = os.path.join(os.path.dirname(__file__), "sql", "create_logs_table.sql")
        with open(migration_path, 'r') as f:
            migration_sql = f.read()
        
        # Apply the migration
        await database.execute(migration_sql)
        print("✅ Applied logs table migration successfully")
        
        # Verify the table was created
        verify_query = """
        SELECT table_name, column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'application_logs' 
        ORDER BY ordinal_position
        """
        
        columns = await database.fetch_all(verify_query)
        if columns:
            print(f"✅ Verified application_logs table created with {len(columns)} columns:")
            for col in columns:
                print(f"   - {col['column_name']}: {col['data_type']}")
        else:
            print("❌ Could not verify table creation")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error applying logs migration: {e}")
        return False
    finally:
        await database.disconnect()


if __name__ == "__main__":
    success = asyncio.run(apply_logs_migration())
    exit(0 if success else 1)