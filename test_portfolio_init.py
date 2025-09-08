#!/usr/bin/env python3
"""
Test script to debug portfolio initialization
"""
import asyncio
import os
import sys

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_portfolio_init():
    """Test the portfolio initialization process"""
    print("🔍 Testing portfolio initialization...")
    
    try:
        # Import after path setup
        from database import init_database, get_portfolio_id, PORTFOLIO_ID, database
        
        print(f"📝 _REPO_NAME environment variable: {os.getenv('_REPO_NAME', 'NOT SET')}")
        print(f"📝 DATABASE_URL environment variable: {os.getenv('DATABASE_URL', 'NOT SET')[:50]}...")
        print(f"📝 _DATABASE_URL environment variable: {os.getenv('_DATABASE_URL', 'NOT SET')[:50]}...")
        
        # Initialize the database
        print("🔄 Calling init_database()...")
        await init_database()
        
        print(f"✅ Portfolio ID after init: {PORTFOLIO_ID}")
        print(f"✅ get_portfolio_id() returns: {get_portfolio_id()}")
        
        # Test a simple query
        print("🔄 Testing database query...")
        portfolios = await database.fetch_all("SELECT id, portfolio_id, name FROM portfolios")
        print(f"📋 Found {len(portfolios)} portfolio records:")
        for p in portfolios:
            print(f"   - ID: {p['id']}, portfolio_id: {p['portfolio_id']}, name: {p['name']}")
        
        # Test logging
        print("🔄 Testing logging...")
        from log_capture import add_log
        add_log("INFO", "Test log from portfolio init script", "test_script")
        print("✅ Log added")
        
        # Check logs in database
        logs = await database.fetch_all("SELECT COUNT(*) as count FROM app_log")
        print(f"📋 Found {logs[0]['count']} log records in database")
        
        await database.disconnect()
        print("✅ Test completed successfully")
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_portfolio_init())
