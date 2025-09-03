"""
Log capture utility for the application.
Provides in-memory logging functionality for debugging and admin monitoring.
"""

import time
from typing import List, Dict, Any
from collections import defaultdict
import threading

# Thread-safe storage for logs
_logs = []
_log_lock = threading.Lock()


def add_log(level: str, source: str, message: str, **kwargs):
    """Add a log entry to the in-memory store."""
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


def get_logs() -> List[Dict[str, Any]]:
    """Get all current log entries."""
    with _log_lock:
        return _logs.copy()


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


# Add some initial test logs for debugging
add_log("INFO", "system", "Log capture module initialized")
add_log("DEBUG", "startup", "Application starting up")
