import logging
import threading
from collections import deque
from typing import List, Dict, Any
from datetime import datetime


class LogCapture:
    """Thread-safe log capture system for web viewing"""
    
    def __init__(self, max_logs: int = 1000):
        self.max_logs = max_logs
        self.logs = deque(maxlen=max_logs)
        self.lock = threading.RLock()
        self.stats = {
            'total': 0,
            'errors': 0,
            'warnings': 0,
            'info': 0,
            'debug': 0,
            'critical': 0
        }
    
    def add_log(self, record: logging.LogRecord):
        """Add a log record to the capture"""
        with self.lock:
            log_entry = {
                'id': self.stats['total'],
                'timestamp': datetime.fromtimestamp(
                    record.created).isoformat(),
                'level': record.levelname,
                'source': record.name,
                'message': record.getMessage(),
                'module': getattr(record, 'module', ''),
                'funcName': getattr(record, 'funcName', ''),
                'lineno': getattr(record, 'lineno', 0)
            }
            
            self.logs.append(log_entry)
            self.stats['total'] += 1
            level = record.levelname.lower()
            self.stats[level] = self.stats.get(level, 0) + 1
    
    def get_logs(self, limit: int = None) -> List[Dict[str, Any]]:
        """Get all captured logs"""
        with self.lock:
            logs_list = list(self.logs)
            if limit:
                logs_list = logs_list[-limit:]
            return logs_list
    
    def get_stats(self) -> Dict[str, int]:
        """Get log statistics"""
        with self.lock:
            return self.stats.copy()
    
    def clear_logs(self):
        """Clear all captured logs"""
        with self.lock:
            self.logs.clear()
            self.stats = {
                'total': 0,
                'errors': 0,
                'warnings': 0,
                'info': 0,
                'debug': 0,
                'critical': 0
            }


class WebLogHandler(logging.Handler):
    """Custom log handler that captures logs for web viewing"""
    
    def __init__(self, log_capture: LogCapture):
        super().__init__()
        self.log_capture = log_capture
    
    def emit(self, record):
        """Emit a log record"""
        try:
            self.log_capture.add_log(record)
        except Exception:
            # Don't let logging errors break the application
            pass


# Global log capture instance
log_capture = LogCapture(max_logs=2000)

# Set up the web log handler
web_handler = WebLogHandler(log_capture)
web_handler.setLevel(logging.DEBUG)

# Add the handler to the root logger to capture all logs
root_logger = logging.getLogger()
root_logger.addHandler(web_handler)

# Also add to specific loggers we care about
logger_names = ['auth', 'main', 'uvicorn', 'uvicorn.access', 'uvicorn.error']
for logger_name in logger_names:
    logger = logging.getLogger(logger_name)
    logger.addHandler(web_handler)
