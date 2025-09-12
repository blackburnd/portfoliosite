"""
Site Configuration Management System
Centralized configuration management for portfolio site customization
"""
import os
from typing import Dict, Any, Optional
from database import database, get_portfolio_id


class SiteConfigManager:
    """Manages site configuration stored in database with fallback to env vars"""
    
    _config_cache: Dict[str, Any] = {}
    _cache_loaded = False
    
    @classmethod
    async def get_config(cls, key: str, default: str = "") -> str:
        """Get a configuration value by key"""
        if not cls._cache_loaded:
            await cls._load_config()
        
        # Check cache first
        if key in cls._config_cache:
            return cls._config_cache[key]
        
        # Check environment variables as fallback
        env_value = os.environ.get(f"SITE_{key.upper()}")
        if env_value:
            return env_value
        
        return default
    
    @classmethod
    async def get_all_config(cls) -> Dict[str, str]:
        """Get all configuration values as a dictionary"""
        if not cls._cache_loaded:
            await cls._load_config()
        
        return cls._config_cache.copy()
    
    @classmethod
    async def set_config(cls, key: str, value: str, description: str = ""):
        """Set a configuration value"""
        portfolio_id = get_portfolio_id()
        
        # Insert or update in database
        query = """
        INSERT INTO site_config (portfolio_id, config_key, config_value, description, updated_at)
        VALUES (:portfolio_id, :key, :value, :description, NOW())
        ON CONFLICT (portfolio_id, config_key)
        DO UPDATE SET 
            config_value = EXCLUDED.config_value,
            description = EXCLUDED.description,
            updated_at = NOW()
        """
        
        await database.execute(query, {
            "portfolio_id": portfolio_id,
            "key": key,
            "value": value,
            "description": description
        })
        
        # Update cache
        cls._config_cache[key] = value
    
    @classmethod
    async def delete_config(cls, key: str):
        """Delete a configuration value from database"""
        from database import database, get_portfolio_id
        
        portfolio_id = get_portfolio_id()
        
        query = """
        DELETE FROM site_config 
        WHERE portfolio_id = :portfolio_id AND config_key = :key
        """
        
        await database.execute(query, {
            "portfolio_id": portfolio_id,
            "key": key
        })
        
        # Remove from cache
        if key in cls._config_cache:
            del cls._config_cache[key]
    
    @classmethod
    async def _load_config(cls):
        """Load all configuration from database into cache"""
        portfolio_id = get_portfolio_id()
        
        query = """
        SELECT config_key, config_value 
        FROM site_config 
        WHERE portfolio_id = :portfolio_id
        ORDER BY config_key
        """
        
        rows = await database.fetch_all(query, {"portfolio_id": portfolio_id})
        
        cls._config_cache = {}
        for row in rows:
            cls._config_cache[row['config_key']] = row['config_value']
        
        cls._cache_loaded = True
    
    @classmethod
    def clear_cache(cls):
        """Clear the configuration cache to force reload"""
        cls._config_cache = {}
        cls._cache_loaded = False
    
    @classmethod
    async def get_config_with_env_fallback(cls, key: str, env_key: str = None, default: str = "") -> str:
        """Get config with specific environment variable fallback"""
        config_value = await cls.get_config(key, "")
        if config_value:
            return config_value
        
        # Use specific env key or construct from config key
        env_var = env_key or f"SITE_{key.upper()}"
        return os.environ.get(env_var, default)
import os
from typing import Dict, Optional, Any
from database import database, get_portfolio_id


class SiteConfigManager:
    """Manages site-wide configuration values stored in the database"""
    
    _config_cache: Dict[str, Any] = {}
    _cache_loaded = False
    
    @classmethod
    async def get_config(cls, key: str, default: Optional[str] = None) -> str:
        """Get a configuration value by key"""
        if not cls._cache_loaded:
            await cls._load_config()
        
        return cls._config_cache.get(key, default or "")
    
    @classmethod
    async def get_all_config(cls) -> Dict[str, Any]:
        """Get all configuration values"""
        if not cls._cache_loaded:
            await cls._load_config()
        
        return cls._config_cache.copy()
    
    @classmethod
    async def _load_config(cls):
        """Load all configuration from database into cache"""
        try:
            portfolio_id = get_portfolio_id()
            if not portfolio_id:
                cls._load_fallback_config()
                return
            
            query = """
            SELECT config_key, config_value 
            FROM site_config 
            WHERE portfolio_id = :portfolio_id
            """
            
            rows = await database.fetch_all(query, {"portfolio_id": portfolio_id})
            
            cls._config_cache = {}
            for row in rows:
                cls._config_cache[row["config_key"]] = row["config_value"]
            
            # Load fallback values for any missing keys
            cls._load_fallback_config(fill_missing_only=True)
            cls._cache_loaded = True
            
        except Exception as e:
            print(f"Warning: Could not load site config from database: {e}")
            cls._load_fallback_config()
    
    @classmethod
    def _load_fallback_config(cls, fill_missing_only: bool = False):
        """Load fallback configuration values"""
        fallback_config = {
            # Site branding
            'site_title': os.getenv('SITE_TITLE', 'Professional Portfolio'),
            'site_tagline': os.getenv('SITE_TAGLINE', 'Building Better Solutions Through Experience'),
            'company_name': os.getenv('COMPANY_NAME', 'Portfolio Systems'),
            'copyright_name': os.getenv('COPYRIGHT_NAME', 'Portfolio Owner'),
            
            # Page titles
            'work_page_title': 'Featured projects and work experience',
            'projects_page_title': 'Featured Projects',
            'admin_work_title': 'Work Items Admin',
            'admin_projects_title': 'Projects Admin',
            
            # Hero content
            'hero_heading': 'Building Better Solutions Through Experience',
            'hero_description': 'With experience across diverse environments, I have learned that foundational knowledge combined with effective communication creates lasting impact. I thrive by embracing continuous growth and approaching every challenge with the mindset of a lifelong learner.',
            'hero_quote': 'Building is easy. Building better is rewarding. Evidence-based performance enhancements are the ultimate motivator.',
            
            # About section
            'about_heading': 'About Me',
            'about_paragraph1': 'With extensive experience solving problems and architecting solutions, I appreciate the deep knowledge that comes from curiosity, trial, and hands-on problem solving. My career has taken me through diverse environments where I\'ve learned that the best solutions often require looking beyond the obvious tools.',
            'about_paragraph2': 'I enjoy working with forward-thinking, collaborative teams to create time-saving toolsets and validate confidence through comprehensive test coverage. Practicing continuous improvement with clear communication, kindness, and empathy helps me work smarter and more sustainably.',
            
            # Current focus section
            'focus_heading': 'Embracing Innovation',
            'focus_description': 'Technology is evolving rapidly, and it\'s an exciting time to be skilled in software development. I focus on leveraging modern tools and methodologies while maintaining strong fundamentals and best practices to deliver robust, scalable solutions.',
            
            # File paths and assets
            'profile_image_path': '/assets/files/profile.png',
            'profile_image_alt': 'Professional headshot',
            'resume_filename': 'resume.pdf',
            
            # OAuth and system messages
            'oauth_success_message': 'You have successfully logged in to your portfolio.',
            'oauth_source_name': 'Portfolio OAuth API',
            
            # Service configuration
            'service_description': 'Professional Portfolio FastAPI Application',
            'service_user': 'portfolio'
        }
        
        if fill_missing_only:
            # Only add keys that don't exist in cache
            for key, value in fallback_config.items():
                if key not in cls._config_cache:
                    cls._config_cache[key] = value
        else:
            # Replace entire cache with fallback
            cls._config_cache = fallback_config
            cls._cache_loaded = True
    
    @classmethod
    async def set_config(cls, key: str, value: str, description: str = "") -> bool:
        """Set a configuration value"""
        try:
            portfolio_id = get_portfolio_id()
            if not portfolio_id:
                return False
            
            query = """
            INSERT INTO site_config (portfolio_id, config_key, config_value, description)
            VALUES (:portfolio_id, :key, :value, :description)
            ON CONFLICT (portfolio_id, config_key)
            DO UPDATE SET 
                config_value = EXCLUDED.config_value,
                description = EXCLUDED.description,
                updated_at = NOW()
            """
            
            await database.execute(query, {
                "portfolio_id": portfolio_id,
                "key": key,
                "value": value,
                "description": description
            })
            
            # Update cache
            cls._config_cache[key] = value
            return True
            
        except Exception as e:
            print(f"Error setting config {key}: {e}")
            return False
    
    @classmethod
    def clear_cache(cls):
        """Clear the configuration cache"""
        cls._config_cache = {}
        cls._cache_loaded = False


# Convenience functions for templates
async def get_site_config(key: str, default: str = "") -> str:
    """Template helper function to get site configuration"""
    return await SiteConfigManager.get_config(key, default)


async def get_site_title() -> str:
    """Get the site title"""
    return await SiteConfigManager.get_config('site_title', 'Professional Portfolio')


async def get_company_name() -> str:
    """Get the company/brand name"""
    return await SiteConfigManager.get_config('company_name', 'Portfolio Systems')
