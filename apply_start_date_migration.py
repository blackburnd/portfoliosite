#!/usr/bin/env python3

import os
import asyncio
import databases


async def apply_migration():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL environment variable not set")
        return
    
    database = databases.Database(database_url)
    
    try:
        await database.connect()
        print("✅ Connected to database")
        
        # Apply the migration
        migration_sql = ("ALTER TABLE work_experience "
                         "ALTER COLUMN start_date DROP NOT NULL;")
        await database.execute(migration_sql)
        print("✅ Migration applied: start_date is now nullable")
        
    except Exception as e:
        print(f"❌ Error applying migration: {e}")
    finally:
        await database.disconnect()

if __name__ == "__main__":
    asyncio.run(apply_migration())
