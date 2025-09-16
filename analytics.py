# analytics.py - Simple analytics tracking system
import os
from datetime import datetime, timedelta
from typing import Dict, Any
from fastapi import Request
from database import database
from log_capture import add_log
from ip_analysis import ip_analyzer


class Analytics:
    """Simple analytics system for tracking page views."""

    def __init__(self):
        self.enabled = os.getenv("ANALYTICS_ENABLED", "true").lower() == "true"

    async def track_page_view(
        self,
        request: Request,
        page_path: str,
        mouse_activity: bool = False
    ):
        """Track a page view with IP analysis and bot detection."""
        if not self.enabled:
            return

        try:
            # Get basic request info
            user_agent = request.headers.get("user-agent", "")
            referer = request.headers.get("referer", "")
            client_ip = self._get_client_ip(request)

            # Perform IP analysis WITHOUT mouse_activity dependency
            # to avoid circular reference
            ip_analysis = await ip_analyzer.analyze_ip_basic(
                client_ip, user_agent
            )

            # Store in database with basic IP analysis data
            # visitor_type will be updated later when mouse activity is known
            query = """
            INSERT INTO page_analytics
            (timestamp, page_path, ip_address, user_agent, referer,
             mouse_activity, reverse_dns, visitor_type, is_datacenter, 
             asn, organization)
            VALUES (:timestamp, :page_path, :ip_address, :user_agent,
                    :referer, :mouse_activity, :reverse_dns, :visitor_type,
                    :is_datacenter, :asn, :organization)
            """

            await database.execute(query, {
                'timestamp': datetime.utcnow(),
                'page_path': page_path,
                'ip_address': client_ip,
                'user_agent': user_agent,
                'referer': referer,
                'mouse_activity': mouse_activity,
                'reverse_dns': ip_analysis.get('reverse_dns'),
                'visitor_type': 'pending',  # Will be updated with mouse activity
                'is_datacenter': ip_analysis.get('is_datacenter', False),
                'asn': ip_analysis.get('asn'),
                'organization': ip_analysis.get('organization')
            })

        except Exception as e:
            # Don't let analytics errors break the site
            add_log(
                "WARNING", "analytics",
                f"Analytics tracking error: {str(e)}",
                function="track_page_view"
            )

    async def track_mouse_activity(self, request: Request, page_path: str):
        """Update existing page view record to mark mouse activity detected"""
        if not self.enabled:
            return

        try:
            client_ip = self._get_client_ip(request)
            
            # First check if there are any matching records
            check_query = """
            SELECT timestamp, mouse_activity
            FROM page_analytics
            WHERE ip_address = :ip_address
                AND page_path = :page_path
                AND timestamp > (NOW() - INTERVAL '5 minutes')
            ORDER BY timestamp DESC
            LIMIT 3
            """
            
            existing_records = await database.fetch_all(check_query, {
                'ip_address': client_ip,
                'page_path': page_path
            })
            
            add_log(
                "INFO", "analytics",
                f"Mouse activity for {client_ip} on {page_path}: "
                f"Found {len(existing_records)} recent records",
                function="track_mouse_activity"
            )
            
            # Update the most recent visit from this IP for this page
            # to mark mouse activity and update visitor classification
            query = """
            UPDATE page_analytics
            SET mouse_activity = TRUE,
                visitor_type = 'human'
            WHERE ip_address = :ip_address
                AND page_path = :page_path
                AND timestamp > (NOW() - INTERVAL '5 minutes')
                AND (mouse_activity = FALSE OR mouse_activity IS NULL)
            """
            
            result = await database.execute(query, {
                'ip_address': client_ip,
                'page_path': page_path
            })
            
            add_log(
                "INFO", "analytics",
                f"Mouse activity update for {client_ip}: "
                f"Updated {result} records",
                function="track_mouse_activity"
            )

        except Exception as e:
            add_log(
                "WARNING", "analytics",
                f"Mouse activity tracking error: {str(e)}",
                function="track_mouse_activity"
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

            # Human visitors (by IP with mouse activity)
            human_visitors = await database.fetch_one(
                """SELECT COUNT(DISTINCT ip_address) as human
                FROM page_analytics 
                WHERE timestamp >= :since_date AND mouse_activity = true""",
                {'since_date': since_date}
            )

            # Visitor type breakdown
            visitor_types = await database.fetch_all(
                """SELECT visitor_type, COUNT(DISTINCT ip_address) as count
                FROM page_analytics 
                WHERE timestamp >= :since_date AND visitor_type IS NOT NULL
                GROUP BY visitor_type
                ORDER BY count DESC""",
                {'since_date': since_date}
            )

            # Bot vs Human stats
            bot_stats = await database.fetch_one(
                """SELECT 
                    COUNT(DISTINCT CASE WHEN visitor_type = 'bot' THEN ip_address END) as bot_visitors,
                    COUNT(DISTINCT CASE WHEN visitor_type = 'human' THEN ip_address END) as confirmed_human_visitors,
                    COUNT(DISTINCT CASE WHEN is_datacenter = true THEN ip_address END) as datacenter_visitors
                FROM page_analytics 
                WHERE timestamp >= :since_date""",
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
            recent_visits_raw = await database.fetch_all(
                """SELECT timestamp, page_path, ip_address
                FROM page_analytics
                WHERE timestamp >= :since_date
                ORDER BY timestamp DESC
                LIMIT 20""",
                {'since_date': since_date}
            )
            
            # Convert timestamps to strings for JSON serialization
            recent_visits = []
            for row in recent_visits_raw:
                row_dict = dict(row)
                if row_dict['timestamp']:
                    row_dict['timestamp'] = row_dict['timestamp'].strftime(
                        '%Y-%m-%d %H:%M:%S')
                recent_visits.append(row_dict)

            # Daily views for chart
            daily_views_raw = await database.fetch_all(
                """SELECT DATE(timestamp) as date, COUNT(*) as views
                FROM page_analytics
                WHERE timestamp >= :since_date
                GROUP BY DATE(timestamp)
                ORDER BY date""",
                {'since_date': since_date}
            )
            
            # Convert dates to strings for JSON serialization
            daily_views = []
            for row in daily_views_raw:
                row_dict = dict(row)
                if row_dict['date']:
                    row_dict['date'] = row_dict['date'].strftime('%Y-%m-%d')
                daily_views.append(row_dict)

            return {
                'total_views': total_views['total'] if total_views else 0,
                'unique_visitors': (unique_visitors['unique']
                                    if unique_visitors else 0),
                'human_visitors': (human_visitors['human']
                                   if human_visitors else 0),
                'visitor_types': [dict(row) for row in visitor_types],
                'bot_visitors': (bot_stats['bot_visitors'] 
                                if bot_stats else 0),
                'confirmed_human_visitors': (bot_stats['confirmed_human_visitors']
                                           if bot_stats else 0),
                'datacenter_visitors': (bot_stats['datacenter_visitors']
                                       if bot_stats else 0),
                'top_pages': [dict(row) for row in top_pages],
                'recent_visits': [dict(row) for row in recent_visits],
                'daily_views': daily_views,
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
                'human_visitors': 0,
                'visitor_types': [],
                'bot_visitors': 0,
                'confirmed_human_visitors': 0,
                'datacenter_visitors': 0,
                'top_pages': [],
                'recent_visits': [],
                'daily_views': [],
                'period_days': days,
                'error': str(e)
            }

    async def get_recent_visits_paginated(
        self, 
        offset: int = 0, 
        limit: int = 50, 
        days: int = 30,
        search: str = None,
        sort_field: str = 'timestamp',
        sort_order: str = 'desc'
    ):
        """Get paginated recent visits with search and sorting"""
        try:
            since_date = datetime.utcnow() - timedelta(days=days)
            
            # Validate sort parameters
            valid_sort_fields = {
                'timestamp', 'page_path', 'ip_address', 
                'user_agent', 'referer'
            }
            if sort_field not in valid_sort_fields:
                sort_field = 'timestamp'
            
            if sort_order.lower() not in {'asc', 'desc'}:
                sort_order = 'desc'
            
            # Build WHERE conditions
            where_conditions = ["timestamp >= :since_date"]
            params = {
                'since_date': since_date,
                'limit': limit,
                'offset': offset
            }
            
            # Add search condition
            if search:
                where_conditions.append(
                    "(page_path ILIKE :search OR ip_address ILIKE :search OR "
                    "user_agent ILIKE :search OR referer ILIKE :search)"
                )
                params['search'] = f"%{search}%"
            
            where_clause = " AND ".join(where_conditions)
            
            # Get recent visits with search and sorting
            query = f"""
                SELECT timestamp, page_path, ip_address, user_agent, referer,
                       mouse_activity, visitor_type, reverse_dns, is_datacenter,
                       asn, organization
                FROM page_analytics
                WHERE {where_clause}
                ORDER BY {sort_field} {sort_order.upper()}
                LIMIT :limit OFFSET :offset
            """
            
            recent_visits_raw = await database.fetch_all(query, params)
            
            # Get total count for pagination info
            count_query = f"""
                SELECT COUNT(*) as total
                FROM page_analytics
                WHERE {where_clause}
            """
            count_params = {k: v for k, v in params.items() 
                          if k not in ['limit', 'offset']}
            total_count_result = await database.fetch_one(count_query, count_params)
            total_count = total_count_result['total'] if total_count_result else 0
            
            # Convert timestamps to strings for JSON serialization
            recent_visits = []
            for row in recent_visits_raw:
                row_dict = dict(row)
                if row_dict['timestamp']:
                    row_dict['timestamp'] = row_dict['timestamp'].strftime(
                        '%Y-%m-%d %H:%M:%S')
                recent_visits.append(row_dict)
            
            return {
                'visits': recent_visits,
                'total_count': total_count,
                'has_more': offset + limit < total_count
            }
            
        except Exception as e:
            add_log(
                "ERROR", "analytics",
                f"Failed to get paginated recent visits: {str(e)}",
                function="get_recent_visits_paginated"
            )
            return {
                'visits': [],
                'total_count': 0,
                'has_more': False,
                'error': str(e)
            }

    async def get_unique_visitors(self, days: int = 7):
        """Get unique visitors with their view counts and last visit times"""
        try:
            since_date = datetime.utcnow() - timedelta(days=days)
            
            query = """
                SELECT 
                    ip_address,
                    COUNT(*) as total_views,
                    MAX(timestamp) as last_visit
                FROM page_analytics
                WHERE timestamp >= :since_date
                GROUP BY ip_address
                ORDER BY total_views DESC, last_visit DESC
            """
            
            visitors_raw = await database.fetch_all(query, {
                'since_date': since_date
            })
            
            # Convert timestamps to strings for JSON serialization
            visitors = []
            for row in visitors_raw:
                row_dict = dict(row)
                if row_dict['last_visit']:
                    row_dict['last_visit'] = row_dict['last_visit'].strftime(
                        '%Y-%m-%d %H:%M:%S')
                visitors.append(row_dict)
            
            return {
                'visitors': visitors,
                'total_unique': len(visitors)
            }
            
        except Exception as e:
            add_log(
                "ERROR", "analytics",
                f"Failed to get unique visitors: {str(e)}",
                function="get_unique_visitors"
            )
            return {
                'visitors': [],
                'total_unique': 0,
                'error': str(e)
            }

    async def get_top_referrers(self, days: int = 7):
        """Get top referrers with visit counts for the specified period."""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)

            query = """
            SELECT
                referer,
                COUNT(*) as visit_count,
                COUNT(DISTINCT ip_address) as unique_visitors
            FROM page_analytics
            WHERE timestamp >= :cutoff_date
                AND referer IS NOT NULL
                AND referer != ''
                AND referer != 'Direct'
            GROUP BY referer
            ORDER BY visit_count DESC
            LIMIT 10
            """

            result = await database.fetch_all(
                query, {"cutoff_date": cutoff_date}
            )

            referrers = []
            for row in result:
                row_dict = dict(row)
                # Clean up referrer display
                if row_dict['referer']:
                    # Extract domain from full URL
                    try:
                        from urllib.parse import urlparse
                        parsed = urlparse(row_dict['referer'])
                        row_dict['domain'] = (
                            parsed.netloc or row_dict['referer']
                        )
                    except Exception:
                        row_dict['domain'] = row_dict['referer']
                else:
                    row_dict['domain'] = 'Unknown'
                referrers.append(row_dict)

            return {
                'referrers': referrers,
                'total_referrers': len(referrers)
            }

        except Exception as e:
            add_log(
                "ERROR", "analytics",
                f"Failed to get top referrers: {str(e)}",
                function="get_top_referrers"
            )
            return {
                'referrers': [],
                'total_referrers': 0,
                'error': str(e)
            }

    async def get_top_ips(self, days: int = 7):
        """Get top IP addresses with visit counts for the specified period."""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)

            query = """
            SELECT
                ip_address,
                COUNT(*) as visit_count,
                COUNT(DISTINCT page_path) as unique_pages,
                visitor_type,
                organization,
                MAX(timestamp) as last_visit
            FROM page_analytics
            WHERE timestamp >= :cutoff_date
                AND ip_address IS NOT NULL
            GROUP BY ip_address, visitor_type, organization
            ORDER BY visit_count DESC
            LIMIT 10
            """

            result = await database.fetch_all(
                query, {"cutoff_date": cutoff_date}
            )

            ips = []
            for row in result:
                row_dict = dict(row)
                if row_dict['last_visit']:
                    row_dict['last_visit'] = row_dict['last_visit'].strftime(
                        '%Y-%m-%d %H:%M:%S')
                ips.append(row_dict)

            return {
                'ips': ips,
                'total_ips': len(ips)
            }

        except Exception as e:
            add_log(
                "ERROR", "analytics",
                f"Failed to get top IPs: {str(e)}",
                function="get_top_ips"
            )
            return {
                'ips': [],
                'total_ips': 0,
                'error': str(e)
            }


# Global analytics instance
analytics = Analytics()
