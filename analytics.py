# analytics.py - Privacy-focused portfolio analytics system
import os
import hashlib
import json
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import Request
from database import database
from log_capture import add_log


class PrivacyAnalytics:
    """
    Privacy-focused analytics system that tracks site usage without
    collecting personal data or requiring user consent.
    """

    def __init__(self):
        self.enabled = os.getenv("ANALYTICS_ENABLED", "true").lower() == "true"

    async def track_page_view(self, request: Request, page_path: str):
        """
        Track a page view with privacy-focused data collection.
        No personal data is stored - only aggregated usage patterns.
        """
        if not self.enabled:
            return

        try:
            # Get basic request info
            user_agent = request.headers.get("user-agent", "")
            referer = request.headers.get("referer", "")
            client_ip = self._get_client_ip(request)
            
            # Create privacy-preserving visitor hash
            # This allows us to count unique visitors without storing IP addresses
            visitor_hash = self._create_visitor_hash(client_ip, user_agent)
            
            # Parse browser and device info (privacy-safe)
            browser_info = self._parse_user_agent(user_agent)
            
            # Get country from IP (no city/precise location)
            country = self._get_country_from_ip(client_ip)
            
            # Clean referrer (remove query params for privacy)
            clean_referer = self._clean_referer(referer)

            # Prepare analytics data
            analytics_data = {
                'timestamp': datetime.utcnow(),
                'page_path': page_path,
                'visitor_hash': visitor_hash,
                'country': country,
                'browser_family': browser_info.get('browser'),
                'browser_version': browser_info.get('version'),
                'device_type': browser_info.get('device_type'),
                'os_family': browser_info.get('os'),
                'referer_domain': clean_referer,
                'is_bot': browser_info.get('is_bot', False)
            }

            # Store in database
            await self._store_analytics(analytics_data)

            # Update page view counters
            await self._update_page_counters(page_path)

        except Exception as e:
            # Don't let analytics errors break the site
            add_log(
                "WARNING", "analytics", 
                f"Analytics tracking error: {str(e)}", 
                function="track_page_view"
            )

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP from request headers (for hashing only)"""
        # Check for forwarded IP first (from nginx/proxy)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
            
        return request.client.host if request.client else "unknown"

    def _create_visitor_hash(self, ip: str, user_agent: str) -> str:
        """
        Create a privacy-preserving visitor hash.
        This allows counting unique visitors without storing IP addresses.
        Hash includes IP + User Agent + daily salt to prevent tracking across days.
        """
        # Daily salt prevents long-term tracking
        daily_salt = datetime.utcnow().strftime("%Y-%m-%d")
        
        # Combine IP, User Agent, and daily salt
        data_to_hash = f"{ip}:{user_agent}:{daily_salt}"
        
        # Create SHA256 hash (one-way, can't be reversed)
        return hashlib.sha256(data_to_hash.encode()).hexdigest()[:16]

    def _parse_user_agent(self, user_agent: str) -> Dict[str, Any]:
        """
        Parse user agent string for browser/device info.
        Returns general categories only, no precise fingerprinting.
        """
        if not user_agent:
            return {
                'browser': 'Unknown',
                'version': '',
                'device_type': 'Unknown',
                'os': 'Unknown',
                'is_bot': False
            }

        ua_lower = user_agent.lower()
        
        # Check for bots first
        bot_indicators = ['bot', 'crawler', 'spider', 'scraper', 'monitor']
        is_bot = any(indicator in ua_lower for indicator in bot_indicators)
        
        # Browser detection
        browser = 'Unknown'
        version = ''
        
        if 'chrome' in ua_lower and 'chromium' not in ua_lower:
            browser = 'Chrome'
        elif 'firefox' in ua_lower:
            browser = 'Firefox'
        elif 'safari' in ua_lower and 'chrome' not in ua_lower:
            browser = 'Safari'
        elif 'edge' in ua_lower:
            browser = 'Edge'
        elif 'opera' in ua_lower:
            browser = 'Opera'
        
        # Device type detection
        device_type = 'Desktop'
        if 'mobile' in ua_lower or 'android' in ua_lower:
            device_type = 'Mobile'
        elif 'tablet' in ua_lower or 'ipad' in ua_lower:
            device_type = 'Tablet'
        
        # OS detection (general categories)
        os_family = 'Unknown'
        if 'windows' in ua_lower:
            os_family = 'Windows'
        elif 'mac' in ua_lower or 'darwin' in ua_lower:
            os_family = 'macOS'
        elif 'linux' in ua_lower:
            os_family = 'Linux'
        elif 'android' in ua_lower:
            os_family = 'Android'
        elif 'ios' in ua_lower or 'iphone' in ua_lower or 'ipad' in ua_lower:
            os_family = 'iOS'
        
        return {
            'browser': browser,
            'version': version,
            'device_type': device_type,
            'os': os_family,
            'is_bot': is_bot
        }

    def _get_country_from_ip(self, ip: str) -> str:
        """
        Get country from IP address.
        For now, returns 'Unknown' - can be enhanced with a privacy-focused
        IP geolocation service if needed.
        """
        # Could integrate with a privacy-focused geolocation service
        # that only returns country-level data
        return 'Unknown'

    def _clean_referer(self, referer: str) -> str:
        """
        Clean referer URL to remove query parameters and personal data.
        Only keeps the domain for privacy.
        """
        if not referer:
            return 'Direct'
        
        try:
            from urllib.parse import urlparse
            parsed = urlparse(referer)
            domain = parsed.netloc
            
            # Remove www prefix for consistency
            if domain.startswith('www.'):
                domain = domain[4:]
                
            return domain if domain else 'Direct'
        except:
            return 'Unknown'

    async def _store_analytics(self, data: Dict[str, Any]):
        """Store analytics data in database"""
        query = """
        INSERT INTO page_analytics (
            timestamp, page_path, visitor_hash, country,
            browser_family, browser_version, device_type, os_family,
            referer_domain, is_bot
        ) VALUES (
            :timestamp, :page_path, :visitor_hash, :country,
            :browser_family, :browser_version, :device_type, :os_family,
            :referer_domain, :is_bot
        )
        """
        
        await database.execute(query, data)

    async def _update_page_counters(self, page_path: str):
        """Update page view counters"""
        # Update daily counter
        today = datetime.utcnow().date()
        
        query = """
        INSERT INTO page_view_counters (page_path, date, view_count)
        VALUES (:page_path, :date, 1)
        ON CONFLICT (page_path, date) 
        DO UPDATE SET view_count = page_view_counters.view_count + 1
        """
        
        await database.execute(query, {
            'page_path': page_path,
            'date': today
        })

    async def get_analytics_summary(self, days: int = 30) -> Dict[str, Any]:
        """
        Get analytics summary for the admin dashboard.
        Returns aggregated, non-personal data.
        """
        try:
            since_date = datetime.utcnow() - timedelta(days=days)
            
            # Total page views
            total_views_query = """
            SELECT COUNT(*) as total_views
            FROM page_analytics 
            WHERE timestamp >= :since_date AND is_bot = false
            """
            total_views = await database.fetch_one(total_views_query, {'since_date': since_date})
            
            # Unique visitors (using hashed visitor IDs)
            unique_visitors_query = """
            SELECT COUNT(DISTINCT visitor_hash) as unique_visitors
            FROM page_analytics 
            WHERE timestamp >= :since_date AND is_bot = false
            """
            unique_visitors = await database.fetch_one(unique_visitors_query, {'since_date': since_date})
            
            # Top pages
            top_pages_query = """
            SELECT page_path, COUNT(*) as views
            FROM page_analytics 
            WHERE timestamp >= :since_date AND is_bot = false
            GROUP BY page_path
            ORDER BY views DESC
            LIMIT 10
            """
            top_pages = await database.fetch_all(top_pages_query, {'since_date': since_date})
            
            # Browser breakdown
            browsers_query = """
            SELECT browser_family, COUNT(*) as count
            FROM page_analytics 
            WHERE timestamp >= :since_date AND is_bot = false
            GROUP BY browser_family
            ORDER BY count DESC
            """
            browsers = await database.fetch_all(browsers_query, {'since_date': since_date})
            
            # Device breakdown
            devices_query = """
            SELECT device_type, COUNT(*) as count
            FROM page_analytics 
            WHERE timestamp >= :since_date AND is_bot = false
            GROUP BY device_type
            ORDER BY count DESC
            """
            devices = await database.fetch_all(devices_query, {'since_date': since_date})
            
            # Daily views for chart
            daily_views_query = """
            SELECT DATE(timestamp) as date, COUNT(*) as views
            FROM page_analytics 
            WHERE timestamp >= :since_date AND is_bot = false
            GROUP BY DATE(timestamp)
            ORDER BY date
            """
            daily_views = await database.fetch_all(daily_views_query, {'since_date': since_date})
            
            return {
                'total_views': total_views['total_views'] if total_views else 0,
                'unique_visitors': unique_visitors['unique_visitors'] if unique_visitors else 0,
                'top_pages': [dict(row) for row in top_pages],
                'browsers': [dict(row) for row in browsers],
                'devices': [dict(row) for row in devices],
                'daily_views': [dict(row) for row in daily_views],
                'period_days': days
            }
            
        except Exception as e:
            add_log(
                "ERROR", "analytics", 
                f"Failed to get analytics summary: {str(e)}", 
                function="get_analytics_summary"
            )
            return {
                'total_views': 0,
                'unique_visitors': 0,
                'top_pages': [],
                'browsers': [],
                'devices': [],
                'daily_views': [],
                'period_days': days,
                'error': str(e)
            }


# Global analytics instance
analytics = PrivacyAnalytics()
