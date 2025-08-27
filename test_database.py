#!/usr/bin/env python3
"""
Database connection test script for PostgreSQL
"""
import asyncio
import sys
import os

async def test_database_connection():
    """Test the PostgreSQL database connection"""
    print("Testing PostgreSQL database connection...")
    
    try:
        from database import init_database, close_database, database
        
        print("✓ Database module imported successfully")
        
        # Test connection
        print("🔄 Attempting to connect to database...")
        await init_database()
        print("✅ Database connection successful!")
        
        # Test a simple query
        print("🔄 Testing simple query...")
        result = await database.fetch_one("SELECT 1 as test")
        assert result['test'] == 1
        print("✅ Simple query test passed!")
        
        # Test schema exists
        print("🔄 Checking if portfolios table exists...")
        table_check = await database.fetch_one("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'portfolios'
            );
        """)
        
        if table_check['exists']:
            print("✅ Portfolios table exists!")
            
            # Test fetching portfolio data
            print("🔄 Testing portfolio data fetch...")
            from database import PortfolioDatabase
            portfolio = await PortfolioDatabase.get_portfolio()
            
            if portfolio:
                print(f"✅ Portfolio data found: {portfolio['name']}")
            else:
                print("⚠️  No portfolio data found - run schema initialization")
        else:
            print("⚠️  Portfolios table not found - schema needs to be initialized")
            print("   Run: psql -h <host> -U <user> -d <database> -f sql/schema.sql")
        
        await close_database()
        print("\n✅ Database connection test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Database connection test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run database connection test"""
    print("=== PostgreSQL Database Connection Test ===\n")
    
    # Check if DATABASE_URL is set
    db_url = os.getenv('DATABASE_URL')
    if db_url:
        print(f"🔗 Using DATABASE_URL: {db_url.replace('password', '***')}")
    else:
        print("⚠️  DATABASE_URL not set, using default from database.py")
    
    success = await test_database_connection()
    
    if success:
        print("\n🎉 Database is ready for GraphQL FastAPI application!")
        return 0
    else:
        print("\n❌ Database connection failed. Please check:")
        print("1. PostgreSQL server is running and accessible")
        print("2. DATABASE_URL environment variable is correct")
        print("3. Database and schema have been created")
        print("4. Network connectivity to database host")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)