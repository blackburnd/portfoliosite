"""
Custom logging handler to route Python logging calls to the database.
This ensures all logger.info(), logger.error(), etc. calls also write to our application_logs table.
"""

import logging
import threading
import queue
import asyncio
import atexit
from datetime import datetime


class DatabaseLogHandler(logging.Handler):
    """Custom logging handler that writes to the application_logs database table."""
    
    def __init__(self, level=logging.NOTSET):
        super().__init__(level)
        self.log_queue = queue.Queue()
        self.worker_thread = None
        self.stop_event = threading.Event()
        self._start_worker()
    
    def _start_worker(self):
        """Start the background worker thread for database writes."""
        self.worker_thread = threading.Thread(target=self._worker, daemon=True)
        self.worker_thread.start()
        atexit.register(self._stop_worker)
    
    def _stop_worker(self):
        """Stop the background worker thread."""
        if self.worker_thread:
            self.stop_event.set()
            self.worker_thread.join(timeout=1)
    
    def _worker(self):
        """Background worker that processes log entries and writes to database."""
        while not self.stop_event.is_set():
            try:
                # Get log entry from queue with timeout
                try:
                    log_entry = self.log_queue.get(timeout=0.5)
                except queue.Empty:
                    continue
                
                # Try to write to database
                try:
                    asyncio.run(self._write_to_database(log_entry))
                except Exception as e:
                    # If database write fails, print to console
                    print(f"[DB LOG FALLBACK] {log_entry['level']}: {log_entry['source']}: {log_entry['message']}")
                
                self.log_queue.task_done()
                
            except Exception as e:
                print(f"Error in database log worker: {e}")
    
    async def _write_to_database(self, log_entry):
        """Write a log entry to the database."""
        try:
            from log_capture import add_log
            await add_log(
                level=log_entry['level'],
                source=log_entry['source'],
                message=log_entry['message'],
                extra_data=log_entry.get('extra_data', {})
            )
        except ImportError:
            # Fall back to console if log_capture not available
            print(f"[DB LOG] {log_entry['level']}: {log_entry['source']}: {log_entry['message']}")
    
    def emit(self, record):
        """Process a logging record and queue for database write."""
        try:
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
            
            # Queue for background processing
            log_entry = {
                'level': level,
                'source': source,
                'message': message,
                'extra_data': extra_data,
                'timestamp': datetime.now()
            }
            
            try:
                self.log_queue.put(log_entry, block=False)
            except queue.Full:
                # If queue is full, just print to console
                print(f"[DB LOG QUEUE FULL] {level}: {source}: {message}")
                
        except Exception as e:
            # Don't let logging errors break the application
            print(f"Error in DatabaseLogHandler.emit: {e}")
    
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