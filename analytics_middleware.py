"""
Analytics Middleware
Automatically tracks page views for all routes without manual intervention
"""

from fastapi import Request, Response
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import time
from typing import Callable

from analytics import analytics
from log_capture import add_log


class AnalyticsMiddleware(BaseHTTPMiddleware):
    """Middleware to automatically track analytics on all routes"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        # Routes to exclude from analytics tracking
        self.excluded_paths = {
            '/admin/analytics/api',
            '/admin/analytics/recent-visits',
            '/logs/data',
            '/admin/logs',
            '/admin/sql',
            '/assets',
            '/favicon.ico',
            '/robots.txt',
            '/sitemap.xml'
        }
        # Paths that start with these prefixes will be excluded
        self.excluded_prefixes = {
            '/assets/',
            '/admin/analytics/',
            '/logs/',
            '/admin/logs/',
            '/admin/sql/',
            '/static/',
            '/_next/',
            '/api/'
        }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request and track analytics if appropriate"""
        start_time = time.time()
        
        # Get the path for checking exclusions
        path = request.url.path
        
        # Process the request first
        response = await call_next(request)
        
        # Only track analytics for successful GET requests
        should_track = (
            request.method == "GET" and
            200 <= response.status_code < 400 and
            not self._is_excluded_path(path) and
            not self._is_static_content(response)
        )
        
        if should_track:
            try:
                # Track the page view asynchronously
                await analytics.track_page_view(request, path)
                
                # Log the tracking for debugging
                processing_time = time.time() - start_time
                add_log(
                    "DEBUG", "analytics_middleware",
                    f"Tracked page view: {path} (processed in {processing_time:.3f}s)",
                    function="dispatch"
                )
                
            except Exception as e:
                # Don't let analytics errors break the site
                add_log(
                    "WARNING", "analytics_middleware",
                    f"Failed to track analytics for {path}: {str(e)}",
                    function="dispatch"
                )
        
        return response
    
    def _is_excluded_path(self, path: str) -> bool:
        """Check if path should be excluded from analytics"""
        # Check exact matches
        if path in self.excluded_paths:
            return True
        
        # Check prefix matches
        for prefix in self.excluded_prefixes:
            if path.startswith(prefix):
                return True
        
        return False
    
    def _is_static_content(self, response: Response) -> bool:
        """Check if response is static content that shouldn't be tracked"""
        content_type = response.headers.get("content-type", "")
        
        # Exclude common static content types
        static_types = {
            "text/css",
            "text/javascript",
            "application/javascript",
            "application/json",
            "image/",
            "font/",
            "application/font",
            "text/plain"
        }
        
        for static_type in static_types:
            if content_type.startswith(static_type):
                return True
        
        return False
    
    def _is_redirect_response(self, response: Response) -> bool:
        """Check if response is a redirect"""
        return isinstance(response, RedirectResponse) or (
            300 <= response.status_code < 400
        )