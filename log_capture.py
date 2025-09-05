"""
Log capture utility for the application.
Provides in-memory logging functionality for debugging and admin monitoring.
"""

import time
import os
import re
from datetime import datetime
from typing import List, Dict, Any
from collections import defaultdict
import threading

# Thread-safe storage for logs
_logs = []
_log_lock = threading.Lock()


import asyncio
from databases import Database

def add_log(level: str, source: str, message: str, **kwargs):
    """Add a log entry to the in-memory store and database."""
    with _log_lock:
        log_entry = {
            "id": len(_logs) + 1,
            "timestamp": time.time() * 1000,  # JavaScript timestamp format
            "level": level.upper(),
            "source": source,
            "message": message,
            **kwargs
        }
        _logs.append(log_entry)
        # Keep only the last 1000 log entries to prevent memory issues
        if len(_logs) > 1000:
            _logs.pop(0)
    # Also write to database asynchronously
    asyncio.create_task(write_log_to_db(level, source, message, **kwargs))

async def write_log_to_db(level, source, message, **kwargs):
    # Use DATABASE_URL from environment
    DATABASE_URL = os.getenv("_DATABASE_URL") or os.getenv("DATABASE_URL")
    db = Database(DATABASE_URL)
    await db.connect()
    # Compose extra fields
    extra = kwargs.get("extra") or ""
    user = kwargs.get("user") or None
    function = kwargs.get("function") or None
    line = kwargs.get("line") or None
    module = kwargs.get("module") or source
    timestamp = datetime.utcnow()
    query = """
        INSERT INTO app_log (timestamp, level, message, module, function, line, "user", extra)
        VALUES (:timestamp, :level, :message, :module, :function, :line, :user, :extra)
    """
    values = {
        "timestamp": timestamp,
        "level": level.upper(),
        "message": message,
        "module": module,
        "function": function,
        "line": line,
        "user": user,
        "extra": extra
    }
    try:
        await db.execute(query=query, values=values)
    except Exception as e:
        pass
    await db.disconnect()


def get_logs() -> List[Dict[str, Any]]:
    """Get all logs as a list of dictionaries."""
    with _log_lock:
        return _logs.copy()





def _add_demo_logs():
    """Add some demo log entries for testing."""
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
    for i, (level, source, message) in enumerate(demo_logs):
        log_entry = {
            "id": len(_logs) + 1,
            "timestamp": base_time - (len(demo_logs) - i) * 60000,  # Spread over last hour
            "level": level,
            "source": source,
            "message": message
        }
        _logs.append(log_entry)


def get_stats() -> Dict[str, Any]:
    """Get statistics about the current logs."""
    with _log_lock:
        if not _logs:
            return {
                "total": 0,
                "by_level": {},
                "by_source": {},
                "newest": None,
                "oldest": None
            }
        
        level_counts = defaultdict(int)
        source_counts = defaultdict(int)
        
        for log in _logs:
            level_counts[log["level"]] += 1
            source_counts[log["source"]] += 1
        
        timestamps = [log["timestamp"] for log in _logs]
        
        return {
            "total": len(_logs),
            "by_level": dict(level_counts),
            "by_source": dict(source_counts),
            "newest": max(timestamps) if timestamps else None,
            "oldest": min(timestamps) if timestamps else None
        }


def clear_logs():
    """Clear all log entries."""
    with _log_lock:
        _logs.clear()


# Create a log_capture object that main.py can import
class LogCapture:
    """Log capture object providing the interface expected by main.py"""
    
    @staticmethod
    def get_logs():
        return get_logs()
    
    @staticmethod
    def get_stats():
        return get_stats()
    
    @staticmethod
    def clear_logs():
        return clear_logs()
    
    @staticmethod
    def add_log(level: str, source: str, message: str, **kwargs):
        return add_log(level, source, message, **kwargs)


# Create the instance that main.py expects to import
log_capture = LogCapture()
