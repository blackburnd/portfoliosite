#!/usr/bin/env python3
"""
Demo script to show the complete database logging workflow.
This script demonstrates:
1. Applying the database migration
2. Testing database logging functionality  
3. Showing log retrieval from the database
"""

import os
import sys
import asyncio

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


async def demo_database_logging():
    """Demonstrate the database logging functionality."""
    print("🚀 Database Logging System Demo")
    print("=" * 50)
    
    # Check if database URL is available
    db_url = os.getenv("DATABASE_URL") or os.getenv("_DATABASE_URL")
    if not db_url:
        print("⚠️  No DATABASE_URL found - this demo will use fallback mode")
        print("   To test with real database, set DATABASE_URL environment variable")
        print("   Example: export DATABASE_URL='postgresql://user:pass@localhost/dbname'")
        print()
    else:
        print(f"✅ Database URL found: {db_url[:50]}...")
        print()
        
        # Apply migration
        print("📋 Applying database migration...")
        try:
            from apply_logs_migration import apply_logs_migration
            success = await apply_logs_migration()
            if success:
                print("✅ Migration applied successfully")
            else:
                print("❌ Migration failed")
                return
        except Exception as e:
            print(f"❌ Migration error: {e}")
            return
    
    print("\n🔧 Testing logging functionality...")
    
    # Import after potential migration
    from log_capture import log_capture
    import logging
    from database_logging import setup_database_logging
    
    # Setup database logging for standard Python loggers
    setup_database_logging()
    
    # Create a demo logger
    demo_logger = logging.getLogger("demo_app")
    
    # Test various logging methods
    print("\n📝 Adding log entries...")
    
    # Direct database logging
    await log_capture.add_log("INFO", "demo", "Demo application started")
    await log_capture.add_log("DEBUG", "demo", "Debug information for testing")
    await log_capture.add_log("WARNING", "demo", "This is a warning message")
    await log_capture.add_log("ERROR", "demo", "This is an error for testing")
    
    # Enhanced logging with metadata
    await log_capture.add_log(
        "INFO", 
        "demo_enhanced", 
        "Enhanced log entry with metadata",
        request_id="demo-req-001",
        user_id="demo-user",
        ip_address="127.0.0.1",
        extra_data={"feature": "demo", "version": "1.0"}
    )
    
    # Standard Python logging (goes through our handler)
    demo_logger.info("Standard logger info message")
    demo_logger.warning("Standard logger warning message")
    demo_logger.error("Standard logger error message")
    
    # Give background processing time
    await asyncio.sleep(1)
    
    print("✅ Log entries added")
    
    # Retrieve and display logs
    print("\n📖 Retrieving logs...")
    
    logs = await log_capture.get_logs(limit=20)
    print(f"✅ Retrieved {len(logs)} log entries")
    
    # Display recent logs
    print("\n📋 Recent Log Entries:")
    for i, log in enumerate(logs[:5]):
        timestamp = log['timestamp']
        print(f"   {i+1}. [{log['level']}] {log['source']}: {log['message']}")
        if log.get('request_id'):
            print(f"      Request ID: {log['request_id']}")
        if log.get('extra_data') and log['extra_data']:
            print(f"      Extra: {log['extra_data']}")
    
    # Show statistics
    print("\n📊 Log Statistics:")
    stats = await log_capture.get_stats()
    print(f"   Total logs: {stats.get('total', 0)}")
    print(f"   By level: {stats.get('by_level', {})}")
    print(f"   Errors: {stats.get('errors', 0)}")
    print(f"   Warnings: {stats.get('warnings', 0)}")
    
    # Test filtering
    print("\n🔍 Testing Log Filtering:")
    try:
        error_logs = await log_capture.get_logs(level_filter="ERROR")
        error_count = len([log for log in error_logs if log['level'] == 'ERROR'])
        print(f"   ERROR level logs: {error_count}")
        
        limited_logs = await log_capture.get_logs(limit=3)
        print(f"   Limited to 3 logs: {len(limited_logs)} returned")
    except Exception as e:
        print(f"   Filtering test: {e}")
    
    print("\n" + "=" * 50)
    print("✅ Database logging demo completed successfully!")
    print("\n💡 Next steps:")
    print("   1. Check your database for the 'application_logs' table")
    print("   2. View logs through the web interface at /debug/logs")
    print("   3. Use the logging system in your application code")
    print("   4. Monitor application logs in real-time")


if __name__ == "__main__":
    try:
        asyncio.run(demo_database_logging())
    except KeyboardInterrupt:
        print("\n👋 Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()