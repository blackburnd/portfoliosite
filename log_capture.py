"""
Log capture utility for the application.
Provides database-backed logging functionality for debugging and admin monitoring.
"""

import time
import os
import re
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
from collections import defaultdict
import threading
import uuid

# Import database connection (with lazy loading to avoid circular imports)
_database = None
_database_available = False

def _get_database():
    """Get database instance with lazy loading"""
    global _database, _database_available
    if _database is None and not _database_available:
        try:
            from database import database
            _database = database
            _database_available = True
        except Exception:
            _database_available = False
    return _database


async def add_log(level: str, source: str, message: str, **kwargs):
    """Add a log entry to the database."""
    database = _get_database()
    
    if database and _database_available:
        try:
            # Prepare the log entry data
            log_data = {
                "level": level.upper(),
                "source": source,
                "message": message,
                "timestamp": datetime.now(),
                "request_id": kwargs.get("request_id"),
                "user_id": kwargs.get("user_id"),
                "session_id": kwargs.get("session_id"),
                "ip_address": kwargs.get("ip_address"),
                "user_agent": kwargs.get("user_agent"),
                "extra_data": kwargs.get("extra_data", {})
            }
            
            # Insert into database
            query = """
            INSERT INTO application_logs 
            (level, source, message, timestamp, request_id, user_id, session_id, ip_address, user_agent, extra_data)
            VALUES (:level, :source, :message, :timestamp, :request_id, :user_id, :session_id, :ip_address, :user_agent, :extra_data)
            """
            
            await database.execute(query, log_data)
            
        except Exception as e:
            # If database logging fails, fall back to console logging
            print(f"[LOG FALLBACK] {level}: {source}: {message}")
            print(f"[LOG ERROR] Failed to write to database: {e}")
    else:
        # Fallback to console logging if database not available
        print(f"[LOG] {level}: {source}: {message}")


def add_log_sync(level: str, source: str, message: str, **kwargs):
    """Synchronous wrapper for add_log - creates new event loop if needed"""
    try:
        # Check if we're in an async context
        try:
            loop = asyncio.get_running_loop()
            # We're in an async context, so we can't run coroutines synchronously
            # Just schedule the task and return immediately
            task = asyncio.create_task(add_log(level, source, message, **kwargs))
            return task
        except RuntimeError:
            # No event loop running, create one
            asyncio.run(add_log(level, source, message, **kwargs))
    except Exception:
        # If all else fails, fall back to console logging
        print(f"[LOG FALLBACK] {level}: {source}: {message}")


async def get_logs(limit: int = 1000, level_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get log entries from the database."""
    database = _get_database()
    
    if not database or not _database_available:
        # Fallback to demo logs if database not available
        return _get_demo_logs()
    
    try:
        # Build query with optional level filter
        query = """
        SELECT id, timestamp, level, source, message, request_id, user_id, session_id, 
               ip_address, user_agent, extra_data, created_at
        FROM application_logs
        """
        params = {}
        
        if level_filter:
            query += " WHERE level = :level"
            params["level"] = level_filter.upper()
        
        query += " ORDER BY timestamp DESC LIMIT :limit"
        params["limit"] = limit
        
        results = await database.fetch_all(query, params)
        
        # Convert to the format expected by the frontend
        logs = []
        for row in results:
            log_entry = {
                "id": str(row["id"]),
                "timestamp": row["timestamp"].timestamp() * 1000,  # JavaScript timestamp format
                "level": row["level"],
                "source": row["source"],
                "message": row["message"],
                "request_id": row["request_id"],
                "user_id": row["user_id"],
                "session_id": row["session_id"],
                "ip_address": str(row["ip_address"]) if row["ip_address"] else None,
                "user_agent": row["user_agent"],
                "extra_data": row["extra_data"] or {}
            }
            logs.append(log_entry)
        
        return logs
        
    except Exception as e:
        print(f"Error fetching logs from database: {e}")
        # Fallback to demo logs if database query fails
        return _get_demo_logs()


def _get_demo_logs() -> List[Dict[str, Any]]:
    """Get demo log entries for testing when database is not available."""
    demo_logs = [
        ("INFO", "system", "Portfolio application started successfully"),
        ("INFO", "auth", "User authentication system initialized"),
        ("DEBUG", "database", "Database connection established"),
        ("INFO", "uvicorn", "Server listening on port 8000"),
        ("WARNING", "oauth", "OAuth token refresh recommended"),
        ("INFO", "main", "API endpoints registered"),
        ("DEBUG", "templates", "Template rendering engine loaded"),
        ("INFO", "assets", "Static assets served from /assets"),
        ("ERROR", "linkedin", "LinkedIn API rate limit reached"),
        ("INFO", "logs", "Log capture system active")
    ]
    
    base_time = time.time() * 1000
    logs = []
    for i, (level, source, message) in enumerate(demo_logs):
        log_entry = {
            "id": str(i + 1),
            "timestamp": base_time - (len(demo_logs) - i) * 60000,  # Spread over last hour
            "level": level,
            "source": source,
            "message": message,
            "request_id": None,
            "user_id": None,
            "session_id": None,
            "ip_address": None,
            "user_agent": None,
            "extra_data": {}
        }
        logs.append(log_entry)
    
    return logs


async def get_stats() -> Dict[str, Any]:
    """Get statistics about the current logs."""
    database = _get_database()
    
    if not database or not _database_available:
        return _get_demo_stats()
    
    try:
        # Get total count
        total_query = "SELECT COUNT(*) as total FROM application_logs"
        total_result = await database.fetch_one(total_query)
        total = total_result["total"] if total_result else 0
        
        # Get counts by level
        level_query = """
        SELECT level, COUNT(*) as count 
        FROM application_logs 
        GROUP BY level
        """
        level_results = await database.fetch_all(level_query)
        by_level = {row["level"]: row["count"] for row in level_results}
        
        # Get counts by source
        source_query = """
        SELECT source, COUNT(*) as count 
        FROM application_logs 
        GROUP BY source 
        ORDER BY count DESC 
        LIMIT 10
        """
        source_results = await database.fetch_all(source_query)
        by_source = {row["source"]: row["count"] for row in source_results}
        
        # Get newest and oldest timestamps
        timestamp_query = """
        SELECT MIN(timestamp) as oldest, MAX(timestamp) as newest 
        FROM application_logs
        """
        timestamp_result = await database.fetch_one(timestamp_query)
        
        newest = None
        oldest = None
        if timestamp_result:
            newest = timestamp_result["newest"].timestamp() * 1000 if timestamp_result["newest"] else None
            oldest = timestamp_result["oldest"].timestamp() * 1000 if timestamp_result["oldest"] else None
        
        return {
            "total": total,
            "by_level": by_level,
            "by_source": by_source,
            "newest": newest,
            "oldest": oldest,
            "errors": by_level.get("ERROR", 0),
            "warnings": by_level.get("WARNING", 0)
        }
        
    except Exception as e:
        print(f"Error fetching log stats from database: {e}")
        return _get_demo_stats()


def _get_demo_stats() -> Dict[str, Any]:
    """Get demo statistics for testing."""
    return {
        "total": 10,
        "by_level": {"INFO": 6, "DEBUG": 2, "WARNING": 1, "ERROR": 1},
        "by_source": {"system": 2, "auth": 1, "database": 1, "uvicorn": 1},
        "newest": time.time() * 1000,
        "oldest": (time.time() - 3600) * 1000,
        "errors": 1,
        "warnings": 1
    }


async def clear_logs():
    """Clear all log entries from the database."""
    database = _get_database()
    
    if database and _database_available:
        try:
            query = "DELETE FROM application_logs"
            await database.execute(query)
        except Exception as e:
            print(f"Error clearing logs from database: {e}")
    else:
        print("Database not available - cannot clear logs")


# Add some initial test logs for debugging (will go to database once it's available)
add_log_sync("INFO", "system", "Log capture module initialized")
add_log_sync("DEBUG", "startup", "Application starting up")


# Create a log_capture object that main.py can import
class LogCapture:
    """Log capture object providing the interface expected by main.py"""
    
    @staticmethod
    async def get_logs(limit: int = 1000, level_filter: Optional[str] = None):
        return await get_logs(limit, level_filter)
    
    @staticmethod
    async def get_stats():
        return await get_stats()
    
    @staticmethod
    async def clear_logs():
        return await clear_logs()
    
    @staticmethod
    async def add_log(level: str, source: str, message: str, **kwargs):
        return await add_log(level, source, message, **kwargs)
    
    @staticmethod
    def add_log_sync(level: str, source: str, message: str, **kwargs):
        return add_log_sync(level, source, message, **kwargs)


# Create the instance that main.py expects to import
log_capture = LogCapture()
