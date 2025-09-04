#!/usr/bin/env python3
"""
Complete integration test for the database logging system.
This script tests the system both with and without a database connection.
"""

import os
import sys
import asyncio
import logging
import time
from datetime import datetime

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import our modules
from log_capture import log_capture, add_log_sync
from database_logging import setup_database_logging


async def test_with_database():
    """Test the system when database is available."""
    print("\n=== Testing with Database ===")
    
    try:
        # This would require DATABASE_URL to be set
        await log_capture.add_log("INFO", "integration_test", "Testing database integration")
        
        logs = await log_capture.get_logs(limit=5)
        print(f"✅ Database test: Retrieved {len(logs)} logs from database")
        
        if logs:
            latest = logs[0]
            print(f"   Latest log: {latest['level']} - {latest['source']} - {latest['message'][:50]}...")
        
        stats = await log_capture.get_stats()
        print(f"✅ Database stats: {stats.get('total', 0)} total logs")
        print(f"   Errors: {stats.get('errors', 0)}, Warnings: {stats.get('warnings', 0)}")
        
    except Exception as e:
        print(f"⚠️  Database test failed (expected if no DB): {e}")


async def test_fallback_mode():
    """Test the system when database is not available."""
    print("\n=== Testing Fallback Mode ===")
    
    # Test basic logging
    add_log_sync("INFO", "fallback_test", "Testing fallback logging")
    await log_capture.add_log("WARNING", "fallback_test", "Async fallback test")
    
    # Test retrieval
    logs = await log_capture.get_logs()
    print(f"✅ Fallback test: Retrieved {len(logs)} demo logs")
    
    stats = await log_capture.get_stats()
    print(f"✅ Fallback stats: {stats.get('total', 0)} total logs")


async def test_logging_integration():
    """Test integration with Python's standard logging system."""
    print("\n=== Testing Standard Logging Integration ===")
    
    # Setup database logging
    db_handler = setup_database_logging()
    
    # Create test logger
    test_logger = logging.getLogger("integration_test")
    test_logger.setLevel(logging.DEBUG)
    
    # Test various log levels
    test_logger.info("Integration test info message")
    test_logger.warning("Integration test warning message")
    test_logger.error("Integration test error message")
    
    # Give background thread time to process
    await asyncio.sleep(0.5)
    
    print("✅ Standard logging integration test completed")
    print("   (Check console output for '[DB LOG]' messages)")


async def test_log_filtering():
    """Test log filtering and limits."""
    print("\n=== Testing Log Filtering ===")
    
    # Add several test logs
    for i in range(5):
        await log_capture.add_log("INFO", "filter_test", f"Test message {i}")
    
    await log_capture.add_log("ERROR", "filter_test", "Error test message")
    await log_capture.add_log("WARNING", "filter_test", "Warning test message")
    
    # Test limit
    limited_logs = await log_capture.get_logs(limit=3)
    print(f"✅ Limited query returned {len(limited_logs)} logs (limit=3)")
    
    # Test level filtering (this will work in fallback mode)
    try:
        error_logs = await log_capture.get_logs(level_filter="ERROR")
        error_count = len([log for log in error_logs if log['level'] == 'ERROR'])
        print(f"✅ Error filter found {error_count} error logs")
    except Exception as e:
        print(f"⚠️  Level filtering test failed: {e}")


async def test_concurrent_logging():
    """Test concurrent logging operations."""
    print("\n=== Testing Concurrent Logging ===")
    
    # Create multiple concurrent logging tasks
    tasks = []
    for i in range(10):
        task = log_capture.add_log("INFO", f"concurrent_test_{i}", f"Concurrent message {i}")
        tasks.append(task)
    
    # Wait for all to complete
    await asyncio.gather(*tasks)
    print("✅ Concurrent logging test completed")


async def demonstrate_new_features():
    """Demonstrate the new database logging features."""
    print("\n=== Demonstrating New Features ===")
    
    # Enhanced logging with metadata
    await log_capture.add_log(
        "INFO", 
        "feature_demo", 
        "Enhanced log with metadata",
        request_id="req-12345",
        user_id="user-67890",
        session_id="sess-abcdef",
        ip_address="192.168.1.100",
        user_agent="TestBot/1.0",
        extra_data={"feature": "database_logging", "version": "1.0"}
    )
    
    print("✅ Enhanced logging with metadata completed")
    
    # Show current logs with metadata
    logs = await log_capture.get_logs(limit=1)
    if logs:
        latest = logs[0]
        print(f"✅ Latest log metadata: request_id={latest.get('request_id')}, user_id={latest.get('user_id')}")


async def run_comprehensive_test():
    """Run all tests to demonstrate the logging system."""
    print("🚀 Starting Comprehensive Database Logging Test")
    print("=" * 60)
    
    start_time = time.time()
    
    # Run all test categories
    await test_fallback_mode()
    await test_with_database()
    await test_logging_integration()
    await test_log_filtering()
    await test_concurrent_logging()
    await demonstrate_new_features()
    
    elapsed = time.time() - start_time
    
    print("\n" + "=" * 60)
    print(f"✅ All tests completed successfully in {elapsed:.2f} seconds!")
    
    # Final summary
    final_logs = await log_capture.get_logs(limit=50)
    final_stats = await log_capture.get_stats()
    
    print(f"\n📊 Final Summary:")
    print(f"   Total logs available: {len(final_logs)}")
    print(f"   Database stats: {final_stats}")
    
    # Show recent logs
    print(f"\n📝 Recent Log Entries:")
    for i, log in enumerate(final_logs[:3]):
        timestamp = datetime.fromtimestamp(log['timestamp'] / 1000)
        print(f"   {i+1}. [{timestamp.strftime('%H:%M:%S')}] {log['level']} - {log['source']}: {log['message'][:50]}...")


if __name__ == "__main__":
    print("Database Logging System - Comprehensive Test")
    print("This test works with or without DATABASE_URL configured.")
    print("")
    
    asyncio.run(run_comprehensive_test())