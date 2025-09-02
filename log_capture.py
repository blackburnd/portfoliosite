# Simple log capture utility
import logging
import io
from typing import List

class LogCapture:
    def __init__(self):
        self.logs = []
        self.stream = io.StringIO()
        self.handler = logging.StreamHandler(self.stream)
        self.handler.setLevel(logging.INFO)
        
    def capture_logs(self, logger_name: str = None):
        """Start capturing logs"""
        logger = logging.getLogger(logger_name) if logger_name else logging.getLogger()
        logger.addHandler(self.handler)
        
    def get_logs(self) -> str:
        """Get captured logs"""
        return self.stream.getvalue()
        
    def clear_logs(self):
        """Clear captured logs"""
        self.stream.truncate(0)
        self.stream.seek(0)

# Global instance
log_capture = LogCapture()