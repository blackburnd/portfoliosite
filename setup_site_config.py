#!/usr/bin/env python3
"""
SQL Execution Helper
Execute SQL files individually to avoid prepared statement issues
"""
import asyncio
import os
import sys
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from database import database, init_database


async def execute_sql_file(file_path: str):
    """Execute a single SQL file"""
    try:
        print(f"📁 Reading SQL file: {file_path}")
        with open(file_path, 'r') as file:
            sql_content = file.read().strip()
        
        if not sql_content:
            print(f"⚠️  Empty file: {file_path}")
            return
        
        # Split by semicolons and execute each statement individually
        statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
        
        print(f"🔄 Executing {len(statements)} SQL statements...")
        
        for i, statement in enumerate(statements, 1):
            if statement.strip():
                try:
                    print(f"   Statement {i}/{len(statements)}: {statement[:60]}...")
                    await database.execute(statement)
                    print(f"   ✅ Statement {i} executed successfully")
                except Exception as e:
                    print(f"   ❌ Error in statement {i}: {e}")
                    print(f"   Statement was: {statement}")
                    raise
        
        print(f"✅ Successfully executed all statements in {file_path}")
        
    except Exception as e:
        print(f"❌ Error executing {file_path}: {e}")
        raise


async def main():
    """Execute all SQL files in order"""
    print("🚀 Starting SQL file execution...")
    
    # Initialize database connection
    await init_database()
    
    sql_files = [
        "sql/01_create_table.sql",
        "sql/02_create_index.sql", 
        "sql/03_create_trigger.sql",
        "sql/04_insert_defaults.sql",
        "sql/05_insert_config_defaults.sql"
    ]
    
    for sql_file in sql_files:
        if os.path.exists(sql_file):
            print(f"\n📋 Processing: {sql_file}")
            await execute_sql_file(sql_file)
        else:
            print(f"⚠️  File not found: {sql_file}")
    
    print("\n🎉 All SQL files executed successfully!")
    print("✅ Site configuration system is ready to use!")
    print("🌐 Navigate to /admin/config to start configuring your site")


if __name__ == "__main__":
    asyncio.run(main())
