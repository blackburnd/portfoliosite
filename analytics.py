# analytics.py - Simple analytics tracking system
import os
from datetime import datetime, timedelta
from typing import Dict, Any
from fastapi import Request
from database import database
from log_capture import add_log


class Analytics:
    """Simple analytics system for tracking page views."""

    def __init__(self):
        self.enabled = os.getenv("ANALYTICS_ENABLED", "true").lower() == "true"

    async def track_page_view(self, request: Request, page_path: str):
        """Track a page view with basic information."""
        if not self.enabled:
            return

        try:
            # Get basic request info
            user_agent = request.headers.get("user-agent", "")
            referer = request.headers.get("referer", "")
            client_ip = self._get_client_ip(request)

            # Store in database
            query = """
            INSERT INTO page_analytics
            (timestamp, page_path, ip_address, user_agent, referer)
            VALUES (:timestamp, :page_path, :ip_address, :user_agent, :referer)
            """

            await database.execute(query, {
                'timestamp': datetime.utcnow(),
                'page_path': page_path,
                'ip_address': client_ip,
                'user_agent': user_agent,
                'referer': referer
            })

        except Exception as e:
            # Don't let analytics errors break the site
            add_log(
                "WARNING", "analytics",
                f"Analytics tracking error: {str(e)}",
                function="track_page_view"
            )

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP from request headers"""
        # Check for forwarded IP first (from nginx/proxy)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        return request.client.host if request.client else "unknown"

    async def get_summary(self, days: int = 30) -> Dict[str, Any]:
        """Get analytics summary for the admin dashboard."""
        try:
            since_date = datetime.utcnow() - timedelta(days=days)

            # Total page views
            total_views = await database.fetch_one(
                """SELECT COUNT(*) as total FROM page_analytics
                WHERE timestamp >= :since_date""",
                {'since_date': since_date}
            )

            # Unique visitors (by IP)
            unique_visitors = await database.fetch_one(
                """SELECT COUNT(DISTINCT ip_address) as unique
                FROM page_analytics WHERE timestamp >= :since_date""",
                {'since_date': since_date}
            )

            # Top pages
            top_pages = await database.fetch_all(
                """SELECT page_path, COUNT(*) as views
                FROM page_analytics
                WHERE timestamp >= :since_date
                GROUP BY page_path
                ORDER BY views DESC
                LIMIT 10""",
                {'since_date': since_date}
            )

            # Recent visits
            recent_visits = await database.fetch_all(
                """SELECT timestamp, page_path, ip_address
                FROM page_analytics
                WHERE timestamp >= :since_date
                ORDER BY timestamp DESC
                LIMIT 20""",
                {'since_date': since_date}
            )

            # Daily views for chart
            daily_views = await database.fetch_all(
                """SELECT DATE(timestamp) as date, COUNT(*) as views
                FROM page_analytics
                WHERE timestamp >= :since_date
                GROUP BY DATE(timestamp)
                ORDER BY date""",
                {'since_date': since_date}
            )

            return {
                'total_views': total_views['total'] if total_views else 0,
                'unique_visitors': (unique_visitors['unique']
                                    if unique_visitors else 0),
                'top_pages': [dict(row) for row in top_pages],
                'recent_visits': [dict(row) for row in recent_visits],
                'daily_views': [dict(row) for row in daily_views],
                'period_days': days
            }

        except Exception as e:
            add_log(
                "ERROR", "analytics",
                f"Failed to get analytics summary: {str(e)}",
                function="get_summary"
            )
            return {
                'total_views': 0,
                'unique_visitors': 0,
                'top_pages': [],
                'recent_visits': [],
                'daily_views': [],
                'period_days': days,
                'error': str(e)
            }


# Global analytics instance
analytics = Analytics()
