#!/usr/bin/env python3
"""
Test script for the new database logging functionality.
"""

import os
import sys
import asyncio
import logging
import time
from datetime import datetime

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Setup test environment variables if not set
if not os.getenv("DATABASE_URL") and not os.getenv("_DATABASE_URL"):
    # For testing, we'll skip database tests if no URL is provided
    print("⚠️  No DATABASE_URL set - will test fallback functionality only")

from log_capture import log_capture, add_log_sync
from database_logging import setup_database_logging


async def test_basic_logging():
    """Test basic logging functionality"""
    print("\n=== Testing Basic Logging ===")
    
    # Test synchronous logging
    add_log_sync("INFO", "test", "This is a test log entry")
    add_log_sync("ERROR", "test", "This is a test error")
    add_log_sync("DEBUG", "test", "Debug message with extra data", extra_data={"key": "value"})
    
    # Test asynchronous logging  
    await log_capture.add_log("WARNING", "test", "Async warning message")
    
    print("✅ Basic logging tests completed")


async def test_log_retrieval():
    """Test log retrieval functionality"""
    print("\n=== Testing Log Retrieval ===")
    
    # Get logs
    logs = await log_capture.get_logs()
    print(f"✅ Retrieved {len(logs)} log entries")
    
    if logs:
        latest_log = logs[0]
        print(f"   Latest log: {latest_log['level']} - {latest_log['source']} - {latest_log['message']}")
    
    # Get stats
    stats = await log_capture.get_stats()
    print(f"✅ Retrieved log stats: {stats.get('total', 0)} total logs")
    
    if stats.get('by_level'):
        print(f"   Levels: {stats['by_level']}")


async def test_standard_logging():
    """Test standard Python logging integration"""
    print("\n=== Testing Standard Logger Integration ===")
    
    # Setup database logging
    handler = setup_database_logging()
    
    # Create a test logger
    test_logger = logging.getLogger("test_app")
    
    # Test various log levels
    test_logger.debug("Debug message from standard logger")
    test_logger.info("Info message from standard logger")
    test_logger.warning("Warning message from standard logger")
    test_logger.error("Error message from standard logger")
    
    # Test with exception
    try:
        raise ValueError("Test exception")
    except ValueError:
        test_logger.error("Error with exception", exc_info=True)
    
    print("✅ Standard logging integration tests completed")


async def test_filtering():
    """Test log filtering functionality"""
    print("\n=== Testing Log Filtering ===")
    
    # Add logs with different levels
    await log_capture.add_log("INFO", "filter_test", "Info log for filtering")
    await log_capture.add_log("ERROR", "filter_test", "Error log for filtering")
    await log_capture.add_log("DEBUG", "filter_test", "Debug log for filtering")
    
    # Test filtering by level
    error_logs = await log_capture.get_logs(level_filter="ERROR")
    error_count = len([log for log in error_logs if log['level'] == 'ERROR'])
    print(f"✅ Found {error_count} ERROR level logs")
    
    # Test limit
    limited_logs = await log_capture.get_logs(limit=5)
    print(f"✅ Limited retrieval returned {len(limited_logs)} logs (max 5)")


async def test_database_migration():
    """Test if database migration is needed/works"""
    print("\n=== Testing Database Migration ===")
    
    try:
        # Try to import and use database functionality
        from apply_logs_migration import apply_logs_migration
        
        # This will attempt to apply the migration
        # In a real scenario, this would be run separately
        print("✅ Migration script available")
        print("   To apply migration, run: python apply_logs_migration.py")
        
    except ImportError as e:
        print(f"❌ Could not import migration: {e}")
    except Exception as e:
        print(f"⚠️  Migration available but may need database: {e}")


async def run_all_tests():
    """Run all tests"""
    print("🚀 Starting Database Logging Tests")
    print("=" * 50)
    
    try:
        await test_basic_logging()
        await test_log_retrieval()
        await test_standard_logging()
        await test_filtering()
        await test_database_migration()
        
        print("\n" + "=" * 50)
        print("✅ All tests completed successfully!")
        
        # Show final stats
        stats = await log_capture.get_stats()
        print(f"\nFinal Stats: {stats.get('total', 0)} total logs")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(run_all_tests())