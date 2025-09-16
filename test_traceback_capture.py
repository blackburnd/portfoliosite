#!/usr/bin/env python3
"""
Test script to verify traceback capture in the logging system
"""
import asyncio
import logging
import sys
import os
import traceback

# Add the current directory to the path to import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from log_capture import add_log


def test_simple_error():
    """Test logging a simple error with traceback"""
    try:
        # This will cause a division by zero error
        1 / 0
    except Exception as e:
        # Capture the full traceback
        traceback_text = traceback.format_exc()
        
        # Log using add_log function
        add_log(
            level="ERROR",
            message=f"Division by zero error: {str(e)}",
            module="test_traceback",
            function="test_simple_error",
            line=22,
            traceback_text=traceback_text
        )
        print("✓ Simple error logged with traceback")


def test_nested_error():
    """Test logging a nested error with a more complex traceback"""
    
    def inner_function():
        # This will cause a key error
        data = {"key1": "value1"}
        return data["nonexistent_key"]
    
    def middle_function():
        return inner_function()
    
    try:
        middle_function()
    except Exception as e:
        # Capture the full traceback
        traceback_text = traceback.format_exc()
        
        # Log using add_log function
        add_log(
            level="ERROR",
            message=f"Nested function error: {str(e)}",
            module="test_traceback",
            function="test_nested_error",
            line=45,
            traceback_text=traceback_text
        )
        print("✓ Nested error logged with traceback")


def test_logging_handler():
    """Test using the logging handler directly"""
    logger = logging.getLogger("test_traceback_handler")
    
    try:
        # This will cause an attribute error
        none_value = None
        none_value.some_method()
    except Exception as e:
        # Log using the standard logging interface which should capture
        # traceback
        logger.error(f"Attribute error: {str(e)}", exc_info=True)
        print("✓ Error logged via logging handler with exc_info=True")


async def test_async_error():
    """Test async error logging"""
    try:
        # This will cause a type error
        await "not_awaitable"
    except Exception as e:
        traceback_text = traceback.format_exc()
        
        add_log(
            level="ERROR",
            message=f"Async error: {str(e)}",
            module="test_traceback",
            function="test_async_error",
            line=76,
            traceback_text=traceback_text
        )
        print("✓ Async error logged with traceback")


def main():
    """Run all traceback tests"""
    print("Testing traceback capture in logging system...")
    print("=" * 50)
    
    # Test 1: Simple error
    test_simple_error()
    
    # Test 2: Nested error
    test_nested_error()
    
    # Test 3: Logging handler
    test_logging_handler()
    
    # Test 4: Async error
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(test_async_error())
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(test_async_error())
    
    print("=" * 50)
    print("✓ All traceback tests completed!")
    print("\nNow check the admin logs interface at /admin/logs to verify:")
    print("1. All 4 test errors appear in the log grid")
    print("2. Each error has a traceback column with full stack trace")
    print("3. Tracebacks can be expanded and copied")
    print("4. No truncation occurs in the traceback content")


if __name__ == "__main__":
    main()