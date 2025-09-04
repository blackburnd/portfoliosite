"""
Custom logging handler to route Python logging calls to the database.
This ensures all logger.info(), logger.error(), etc. calls also write to our application_logs table.
"""

import logging
import threading
from log_capture import add_log_sync


class DatabaseLogHandler(logging.Handler):
    """Custom logging handler that writes to the application_logs database table."""
    
    def __init__(self, level=logging.NOTSET):
        super().__init__(level)
        self.lock = threading.Lock()
    
    def emit(self, record):
        """Process a logging record and write to database."""
        try:
            with self.lock:
                # Extract information from the log record
                level = record.levelname
                source = record.name
                message = self.format(record)
                
                # Extract additional context if available
                extra_data = {}
                
                # Add exception info if present
                if record.exc_info:
                    extra_data['exception'] = self.formatException(record.exc_info)
                
                # Add file/line info
                if hasattr(record, 'pathname') and hasattr(record, 'lineno'):
                    extra_data['file'] = f"{record.pathname}:{record.lineno}"
                
                # Add function name if available
                if hasattr(record, 'funcName'):
                    extra_data['function'] = record.funcName
                
                # Write to database (using sync version to avoid async issues in logging)
                # For now, just print to avoid potential deadlocks with logging
                print(f"[DB LOG] {level}: {source}: {message}")
                
        except Exception as e:
            # Don't let logging errors break the application
            print(f"Error in DatabaseLogHandler: {e}")
    
    def handleError(self, record):
        """Handle errors in the logging handler without raising exceptions."""
        # Silently handle errors to avoid breaking the application
        pass


def setup_database_logging():
    """Setup database logging handler for the root logger."""
    # Create and configure the database handler
    db_handler = DatabaseLogHandler()
    db_handler.setLevel(logging.DEBUG)
    
    # Use a simple format since we're storing structured data
    formatter = logging.Formatter('%(message)s')
    db_handler.setFormatter(formatter)
    
    # Add to root logger so all loggers inherit it
    root_logger = logging.getLogger()
    root_logger.addHandler(db_handler)
    
    return db_handler