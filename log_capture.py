"""
Log capture module for writing application logs to the database
"""
import asyncio
import logging
import os
import traceback
from datetime import datetime
from typing import Optional
import json

import databases
from fastapi import Request


def get_database_connection():
    """
    Centralized function to create database connections for logging.
    This ensures consistent database URL handling across logging functions.
    """
    database_url = os.getenv("_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("No database URL found in environment variables")
    return databases.Database(database_url)


def get_client_ip(request: Request) -> str:
    """
    Extract the real client IP address from the request, accounting for proxies and load balancers.
    Checks headers commonly used by reverse proxies and load balancers.
    """
    # Check various proxy headers in order of preference
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For can contain multiple IPs, the first one is usually the original client
        return forwarded_for.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    
    cf_connecting_ip = request.headers.get("CF-Connecting-IP")  # Cloudflare
    if cf_connecting_ip:
        return cf_connecting_ip.strip()
    
    x_forwarded = request.headers.get("X-Forwarded")
    if x_forwarded:
        return x_forwarded.split(",")[0].strip()
    
    # Fall back to the direct client IP
    if request.client:
        return request.client.host
    
    return "unknown"


class DatabaseLogHandler(logging.Handler):
    """Custom logging handler that writes logs to the database"""
    
    def __init__(self, database_url: str = None):
        super().__init__()
        self.database_url = database_url
        self.db = get_database_connection()
        self._loop = None
        
    def emit(self, record: logging.LogRecord):
        """Emit a log record to the database"""
        try:
            # Get or create event loop
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Run the async insert in the loop
            if loop.is_running():
                # If loop is already running, schedule the task
                asyncio.create_task(self._insert_log(record))
            else:
                # If loop is not running, run it
                loop.run_until_complete(self._insert_log(record))
                
        except Exception as e:
            # Fallback to print if database insert fails
            print(f"Failed to insert log to database: {e}")
            print(f"Log record: {record.getMessage()}")
    
    async def _insert_log(self, record: logging.LogRecord):
        """Insert log record into database"""
        try:
            await self.db.connect()
            
            # Extract extra information
            extra = {}
            if hasattr(record, 'exc_info') and record.exc_info:
                extra['traceback'] = ''.join(traceback.format_exception(*record.exc_info))
            
            # Get user info if available
            user = getattr(record, 'user', None)
            # Get IP address if available
            ip_address = getattr(record, 'ip_address', None)
            
            query = """
                INSERT INTO app_log (timestamp, level, message, module,
                                   function, line, user, extra, ip_address)
                VALUES (:timestamp, :level, :message, :module,
                       :function, :line, :user, :extra, :ip_address)
            """
            
            values = {
                'timestamp': datetime.fromtimestamp(record.created),
                'level': record.levelname,
                'message': record.getMessage(),
                'module': (record.module if hasattr(record, 'module')
                           else record.name),
                'function': record.funcName,
                'line': record.lineno,
                'user': user,
                'extra': json.dumps(extra) if extra else None,
                'ip_address': ip_address
            }
            
            await self.db.execute(query, values)
            await self.db.disconnect()
            
        except Exception as e:
            print(f"Database log insert failed: {e}")
            try:
                await self.db.disconnect()
            except Exception:
                pass


# Global log handler instance
_db_log_handler = None


def setup_database_logging():
    """Set up database logging handler"""
    global _db_log_handler
    
    database_url = os.getenv("_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not database_url:
        print("No database URL found, skipping database logging setup")
        return
    
    try:
        _db_log_handler = DatabaseLogHandler(database_url)
        _db_log_handler.setLevel(logging.INFO)
        
        # Add to root logger
        root_logger = logging.getLogger()
        root_logger.addHandler(_db_log_handler)
        
        # Add to specific loggers
        for logger_name in ['uvicorn', 'fastapi', 'app']:
            logger = logging.getLogger(logger_name)
            logger.addHandler(_db_log_handler)
            logger.setLevel(logging.INFO)
        
        print("Database logging handler set up successfully")
        
    except Exception as e:
        print(f"Failed to set up database logging: {e}")


def add_log(level: str, message: str, module: str = "manual",
            function: str = "add_log", line: int = 0,
            user: Optional[str] = None, extra: Optional[dict] = None):
    """Manually add a log entry to the database"""
    async def _add_log_async():
        db = get_database_connection()

        try:
            await db.connect()

            query = """
                INSERT INTO app_log (timestamp, level, message, module,
                                   function, line, "user", extra, ip_address)
                VALUES (:timestamp, :level, :message, :module, :function,
                       :line, :user, :extra, :ip_address)
            """

            values = {
                'timestamp': datetime.now(),
                'level': level.upper(),
                'message': message,
                'module': module,
                'function': function,
                'line': line,
                'user': user,
                'extra': json.dumps(extra) if extra else None,
                'ip_address': None
            }

            await db.execute(query, values)
            await db.disconnect()

        except Exception as e:
            print(f"Failed to add manual log entry: {e}")
            try:
                await db.disconnect()
            except Exception:
                pass

    # Run the async function synchronously
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If loop is already running, schedule the task
            asyncio.create_task(_add_log_async())
        else:
            # If loop is not running, run it
            loop.run_until_complete(_add_log_async())
    except RuntimeError:
        # Create new loop if none exists
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_add_log_async())


async def clear_logs():
    """Clear all logs from the database"""
    db = get_database_connection()
    
    try:
        await db.connect()
        await db.execute("DELETE FROM app_log")
        await db.disconnect()
        print("All logs cleared from database")
        
    except Exception as e:
        print(f"Failed to clear logs: {e}")
        try:
            await db.disconnect()
        except:
            pass


# Legacy compatibility
class LogCapture:
    """Legacy log capture class for compatibility"""
    
    @staticmethod
    def clear_logs():
        """Clear logs - runs async function synchronously"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Create a task if loop is running
                asyncio.create_task(clear_logs())
            else:
                # Run synchronously if no loop
                loop.run_until_complete(clear_logs())
        except RuntimeError:
            # Create new loop if none exists
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(clear_logs())


# Create global instance for legacy compatibility
log_capture = LogCapture()

# Set up database logging when module is imported
setup_database_logging()




def log_with_context(level: str, message: str, module: str = "manual",
                     function: str = "add_log", line: int = 0,
                     user: str = None, extra: dict = None,
                     request=None):
    """Context-aware logging identical to add_log but captures IP address"""
    # Get IP address if request is provided
    ip_address = None
    if request:
        try:
            ip_address = get_client_ip(request)
        except Exception:
            ip_address = "unknown"
    
    async def _add_log_async():
        db = get_database_connection()

        try:
            await db.connect()

            query = """
                INSERT INTO app_log (timestamp, level, message, module,
                                   function, line, "user", extra, ip_address)
                VALUES (:timestamp, :level, :message, :module, :function,
                       :line, :user, :extra, :ip_address)
            """

            values = {
                'timestamp': datetime.now(),
                'level': level.upper(),
                'message': message,
                'module': module,
                'function': function,
                'line': line,
                'user': user,
                'extra': json.dumps(extra) if extra else None,
                'ip_address': ip_address
            }

            await db.execute(query, values)
            await db.disconnect()

        except Exception as e:
            print(f"Failed to add manual log entry: {e}")
            try:
                await db.disconnect()
            except Exception:
                pass

    # Run the async function synchronously
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If loop is already running, schedule the task
            asyncio.create_task(_add_log_async())
        else:
            # If loop is not running, run it
            loop.run_until_complete(_add_log_async())
    except RuntimeError:
        # Create new loop if none exists
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_add_log_async())
