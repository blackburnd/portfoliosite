"""
IP Analysis Module for Enhanced Bot Detection
Provides reverse DNS lookup, network classification, and visitor type detection
"""
import socket
import ipaddress
import requests
import asyncio
from typing import Dict, Optional, Any
from log_capture import add_log


class IPAnalyzer:
    """Analyzes IP addresses for bot detection and visitor classification"""
    
    def __init__(self):
        # Known bot networks (major search engines and common hosting providers)
        self.bot_networks = [
            # Google
            '66.249.64.0/19',    # Googlebot primary
            '64.233.160.0/19',   # Google services
            '172.217.0.0/16',    # Google infrastructure
            
            # Bing/Microsoft
            '40.77.167.0/24',    # Bingbot
            '157.55.39.0/24',    # Microsoft crawlers
            '40.76.0.0/16',      # Microsoft Azure
            
            # Common hosting/VPS providers (often used by bots)
            '104.16.0.0/12',     # Cloudflare
            '162.158.0.0/15',    # Cloudflare
            '173.245.48.0/20',   # Cloudflare
            '198.41.128.0/17',   # Cloudflare
            
            # AWS (many bots/scanners)
            '54.0.0.0/8',        # AWS EC2 (partial)
            '52.0.0.0/8',        # AWS EC2 (partial)
            
            # DigitalOcean (common for VPS bots)
            '104.131.0.0/16',    # DigitalOcean
            '159.89.0.0/16',     # DigitalOcean
            '178.62.0.0/16',     # DigitalOcean
            
            # Vultr (VPS provider)
            '108.61.0.0/16',     # Vultr
            '149.28.0.0/16',     # Vultr
        ]
        
        # Known bot hostname patterns
        self.bot_hostname_patterns = [
            'bot', 'crawler', 'spider', 'scraper', 'scanner',
            'googlebot', 'bingbot', 'slurp', 'facebookexternalhit',
            'twitterbot', 'linkedinbot', 'whatsapp', 'telegram',
            'discord', 'slack', 'zoom'
        ]
        
        # Datacenter/hosting provider patterns
        self.datacenter_patterns = [
            'amazon', 'aws', 'google', 'microsoft', 'azure',
            'digitalocean', 'vultr', 'linode', 'ovh', 'hetzner',
            'cloudflare', 'fastly', 'hosting', 'datacenter',
            'servers', 'vps', 'cloud', 'compute'
        ]
    
    def get_reverse_dns(self, ip_address: str) -> Optional[str]:
        """Get reverse DNS hostname for an IP address"""
        try:
            hostname = socket.gethostbyaddr(ip_address)[0]
            return hostname.lower()
        except (socket.herror, socket.gaierror, OSError):
            return None
    
    def is_known_bot_network(self, ip_address: str) -> bool:
        """Check if IP belongs to a known bot/crawler network"""
        try:
            ip = ipaddress.ip_address(ip_address)
            for network in self.bot_networks:
                if ip in ipaddress.ip_network(network):
                    return True
            return False
        except (ValueError, ipaddress.AddressValueError):
            return False
    
    def analyze_hostname(self, hostname: Optional[str]) -> Dict[str, bool]:
        """Analyze hostname for bot and datacenter indicators"""
        if not hostname:
            return {'is_bot_hostname': False, 'is_datacenter_hostname': False}
        
        hostname_lower = hostname.lower()
        
        is_bot = any(pattern in hostname_lower for pattern in self.bot_hostname_patterns)
        is_datacenter = any(pattern in hostname_lower for pattern in self.datacenter_patterns)
        
        return {
            'is_bot_hostname': is_bot,
            'is_datacenter_hostname': is_datacenter
        }
    
    async def get_ip_geolocation(self, ip_address: str) -> Optional[Dict[str, Any]]:
        """Get IP geolocation and organization info using free API"""
        try:
            # Using ipapi.co free tier (1000 requests/day)
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: requests.get(
                    f"https://ipapi.co/{ip_address}/json/",
                    timeout=5
                )
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'org': data.get('org', ''),
                    'asn': data.get('asn', ''),
                    'city': data.get('city', ''),
                    'country': data.get('country_code', ''),
                    'region': data.get('region', ''),
                    'is_datacenter': self._is_datacenter_org(data.get('org', ''))
                }
        except Exception as e:
            add_log("WARNING", "ip_analyzer", 
                   f"Failed to get geolocation for {ip_address}: {str(e)}")
        
        return None
    
    def _is_datacenter_org(self, org_name: str) -> bool:
        """Check if organization name indicates a datacenter/hosting provider"""
        if not org_name:
            return False
        
        org_lower = org_name.lower()
        return any(pattern in org_lower for pattern in self.datacenter_patterns)
    
    def classify_visitor(self, 
                        ip_address: str,
                        user_agent: str,
                        mouse_activity: bool,
                        reverse_dns: Optional[str] = None,
                        geo_data: Optional[Dict] = None) -> str:
        """
        Classify visitor type based on multiple signals
        Returns: 'human', 'bot', 'suspicious', 'unknown'
        """
        bot_signals = 0
        
        # Mouse activity (strongest human signal)
        if not mouse_activity:
            bot_signals += 1
        
        # User agent analysis
        user_agent_lower = user_agent.lower()
        if any(bot_word in user_agent_lower for bot_word in 
               ['bot', 'crawler', 'spider', 'scraper']):
            bot_signals += 3
        
        # Reverse DNS analysis
        if reverse_dns:
            hostname_analysis = self.analyze_hostname(reverse_dns)
            if hostname_analysis['is_bot_hostname']:
                bot_signals += 3
            elif hostname_analysis['is_datacenter_hostname']:
                bot_signals += 1
        
        # Network analysis
        if self.is_known_bot_network(ip_address):
            bot_signals += 2
        
        # Geolocation analysis
        if geo_data and geo_data.get('is_datacenter'):
            bot_signals += 1
        
        # Classification thresholds
        if bot_signals >= 4:
            return 'bot'
        elif bot_signals >= 2:
            return 'suspicious'
        elif mouse_activity and bot_signals == 0:
            return 'human'
        else:
            return 'unknown'
    
    async def analyze_ip_basic(self,
                               ip_address: str,
                               user_agent: str) -> Dict[str, Any]:
        """
        Perform basic IP analysis without mouse activity dependency
        Returns basic analysis data for initial page view tracking
        """
        try:
            # Reverse DNS lookup
            reverse_dns = self.get_reverse_dns(ip_address)
            
            # Geolocation lookup (with rate limiting consideration)
            geo_data = await self.get_ip_geolocation(ip_address)
            
            return {
                'reverse_dns': reverse_dns,
                'is_datacenter': (
                    geo_data.get('is_datacenter', False) if geo_data 
                    else self.analyze_hostname(reverse_dns).get(
                        'is_datacenter_hostname', False)
                ),
                'asn': geo_data.get('asn') if geo_data else None,
                'organization': geo_data.get('org') if geo_data else None,
                'geo_data': geo_data
            }
            
        except Exception as e:
            add_log("ERROR", "ip_analyzer",
                    f"Failed basic IP analysis for {ip_address}: {str(e)}")
            return {
                'reverse_dns': None,
                'is_datacenter': False,
                'asn': None,
                'organization': None,
                'geo_data': None
            }

    async def analyze_ip_comprehensive(self, 
                                     ip_address: str, 
                                     user_agent: str,
                                     mouse_activity: bool) -> Dict[str, Any]:
        """
        Perform comprehensive IP analysis
        Returns all analysis data for storage
        """
        try:
            # Reverse DNS lookup
            reverse_dns = self.get_reverse_dns(ip_address)
            
            # Geolocation lookup (with rate limiting consideration)
            geo_data = await self.get_ip_geolocation(ip_address)
            
            # Visitor classification
            visitor_type = self.classify_visitor(
                ip_address, user_agent, mouse_activity, reverse_dns, geo_data
            )
            
            return {
                'reverse_dns': reverse_dns,
                'visitor_type': visitor_type,
                'is_datacenter': (
                    geo_data.get('is_datacenter', False) if geo_data 
                    else self.analyze_hostname(reverse_dns).get('is_datacenter_hostname', False)
                ),
                'asn': geo_data.get('asn') if geo_data else None,
                'organization': geo_data.get('org') if geo_data else None,
                'geo_data': geo_data
            }
            
        except Exception as e:
            add_log("ERROR", "ip_analyzer", 
                   f"Failed to analyze IP {ip_address}: {str(e)}")
            return {
                'reverse_dns': None,
                'visitor_type': 'unknown',
                'is_datacenter': False,
                'asn': None,
                'organization': None,
                'geo_data': None
            }


# Global instance
ip_analyzer = IPAnalyzer()