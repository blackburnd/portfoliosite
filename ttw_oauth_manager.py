# ttw_oauth_manager.py - Through-The-Web OAuth Management Service
import os
import json
import logging
import secrets
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from database import database
import httpx

logger = logging.getLogger(__name__)

class TTWOAuthManagerError(Exception):
    """Custom exception for TTW OAuth Manager errors"""
    pass

class TTWOAuthManager:
    """
    Through-The-Web OAuth Management Service
    Complete self-contained LinkedIn OAuth implementation with no environment variables
    """
    
    def __init__(self):
        # Generate or use encryption key (store in database in production)
        encryption_key = self._get_or_create_encryption_key()
        try:
            self.cipher = Fernet(encryption_key.encode() if isinstance(encryption_key, str) else encryption_key)
        except Exception as e:
            logger.error(f"Failed to initialize encryption: {e}")
            raise TTWOAuthManagerError("Invalid encryption key configuration")
        
        # Default redirect URI pattern (will be configurable)
        self.default_redirect_uri_pattern = "/admin/linkedin/callback"
    
    def _get_or_create_encryption_key(self) -> str:
        """Get or create encryption key for OAuth tokens"""
        # In production, this could be stored in database or generated once
        encryption_key = os.getenv("OAUTH_ENCRYPTION_KEY")
        if not encryption_key:
            encryption_key = Fernet.generate_key().decode()
            logger.warning("Generated new encryption key for OAuth tokens. Store OAUTH_ENCRYPTION_KEY securely in production.")
        return encryption_key
    
    def _encrypt_token(self, token: str) -> str:
        """Encrypt a token for secure storage"""
        return self.cipher.encrypt(token.encode()).decode()
    
    def _decrypt_token(self, encrypted_token: str) -> str:
        """Decrypt a token for use"""
        return self.cipher.decrypt(encrypted_token.encode()).decode()
    
    # OAuth App Configuration Methods
    
    async def is_oauth_app_configured(self) -> bool:
        """Check if LinkedIn OAuth app is configured"""
        query = "SELECT COUNT(*) FROM linkedin_oauth_config WHERE is_active = true"
        result = await database.fetch_val(query)
        return result > 0
    
    async def get_oauth_app_config(self) -> Optional[Dict[str, Any]]:
        """Get active LinkedIn OAuth app configuration"""
        query = """
            SELECT app_name, client_id, client_secret, redirect_uri, configured_by_email, created_at
            FROM linkedin_oauth_config 
            WHERE is_active = true
            ORDER BY created_at DESC
            LIMIT 1
        """
        result = await database.fetch_one(query)
        if not result:
            return None
        
        try:
            return {
                "app_name": result["app_name"],
                "client_id": result["client_id"],
                "client_secret": self._decrypt_token(result["client_secret"]),
                "redirect_uri": result["redirect_uri"],
                "configured_by_email": result["configured_by_email"],
                "created_at": result["created_at"]
            }
        except Exception as e:
            logger.error(f"Failed to decrypt OAuth app config: {e}")
            return None
    
    async def configure_oauth_app(self, admin_email: str, app_config: Dict[str, str]) -> bool:
        """Configure LinkedIn OAuth app through admin interface"""
        try:
            # Deactivate existing configs
            await database.execute(
                "UPDATE linkedin_oauth_config SET is_active = false WHERE is_active = true"
            )
            
            # Encrypt client secret
            encrypted_secret = self._encrypt_token(app_config["client_secret"])
            
            # Insert new config
            query = """
                INSERT INTO linkedin_oauth_config 
                (app_name, client_id, client_secret, redirect_uri, configured_by_email)
                VALUES (:app_name, :client_id, :client_secret, :redirect_uri, :admin_email)
            """
            
            await database.execute(query, {
                "app_name": app_config.get("app_name", "Portfolio LinkedIn Integration"),
                "client_id": app_config["client_id"],
                "client_secret": encrypted_secret,
                "redirect_uri": app_config["redirect_uri"],
                "admin_email": admin_email
            })
            
            logger.info(f"LinkedIn OAuth app configured by admin: {admin_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to configure OAuth app: {e}")
            return False
    
    # OAuth Scope Methods
    
    async def get_available_scopes(self) -> List[Dict[str, Any]]:
        """Get available LinkedIn OAuth scopes"""
        query = """
            SELECT scope_name, display_name, description, data_access_description, is_required
            FROM linkedin_oauth_scopes 
            WHERE is_enabled = true
            ORDER BY sort_order, display_name
        """
        results = await database.fetch_all(query)
        return [dict(result) for result in results]
    
    async def get_default_scopes(self) -> List[str]:
        """Get default required scopes"""
        query = """
            SELECT scope_name FROM linkedin_oauth_scopes 
            WHERE is_required = true AND is_enabled = true
            ORDER BY sort_order
        """
        results = await database.fetch_all(query)
        return [result["scope_name"] for result in results]
    
    # OAuth Authorization Methods
    
    async def get_linkedin_authorization_url(self, admin_email: str, requested_scopes: List[str] = None) -> Tuple[str, str]:
        """Generate LinkedIn OAuth authorization URL"""
        config = await self.get_oauth_app_config()
        if not config:
            raise TTWOAuthManagerError("LinkedIn OAuth app not configured. Please configure it first.")
        
        if not requested_scopes:
            requested_scopes = await self.get_default_scopes()
        
        # Generate secure state parameter
        state_data = {
            "admin_email": admin_email,
            "requested_scopes": requested_scopes,
            "timestamp": datetime.utcnow().isoformat(),
            "nonce": secrets.token_urlsafe(16)
        }
        state = self._encrypt_token(json.dumps(state_data))
        
        # Build authorization URL
        params = {
            "response_type": "code",
            "client_id": config["client_id"],
            "redirect_uri": config["redirect_uri"],
            "state": state,
            "scope": " ".join(requested_scopes)
        }
        
        param_string = "&".join([f"{k}={v}" for k, v in params.items()])
        auth_url = f"https://www.linkedin.com/oauth/v2/authorization?{param_string}"
        
        logger.info(f"Generated LinkedIn auth URL for {admin_email} with scopes: {requested_scopes}")
        return auth_url, state
    
    def verify_linkedin_state(self, state: str) -> Dict[str, Any]:
        """Verify and extract data from LinkedIn OAuth state parameter"""
        try:
            state_data = json.loads(self._decrypt_token(state))
            
            # Verify timestamp (state should be used within 10 minutes)
            timestamp = datetime.fromisoformat(state_data["timestamp"])
            if datetime.utcnow() - timestamp > timedelta(minutes=10):
                raise TTWOAuthManagerError("OAuth state expired")
            
            return state_data
        except Exception as e:
            logger.error(f"Failed to verify LinkedIn state: {e}")
            raise TTWOAuthManagerError("Invalid OAuth state parameter")
    
    async def exchange_linkedin_code_for_tokens(self, code: str, state_data: Dict[str, Any]) -> Dict[str, Any]:
        """Exchange LinkedIn authorization code for access tokens"""
        config = await self.get_oauth_app_config()
        if not config:
            raise TTWOAuthManagerError("LinkedIn OAuth app not configured")
        
        admin_email = state_data["admin_email"]
        requested_scopes = state_data["requested_scopes"]
        
        token_data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": config["redirect_uri"],
            "client_id": config["client_id"],
            "client_secret": config["client_secret"],
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    "https://www.linkedin.com/oauth/v2/accessToken",
                    data=token_data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                response.raise_for_status()
                token_response = response.json()
                
                # Get user profile to extract granted scopes and profile info
                profile_data = await self._get_linkedin_profile(token_response["access_token"])
                
                # Store connection with granted permissions
                await self._store_linkedin_connection(
                    admin_email, 
                    token_response, 
                    requested_scopes,
                    profile_data
                )
                
                return {
                    "access_token": token_response["access_token"],
                    "granted_scopes": token_response.get("scope", " ".join(requested_scopes)).split(),
                    "profile": profile_data
                }
                
            except httpx.RequestError as e:
                logger.error(f"LinkedIn token exchange request failed: {e}")
                raise TTWOAuthManagerError(f"Failed to exchange code for tokens: {e}")
            except httpx.HTTPStatusError as e:
                logger.error(f"LinkedIn token exchange HTTP error: {e.response.status_code} - {e.response.text}")
                raise TTWOAuthManagerError(f"LinkedIn token exchange failed: {e.response.status_code}")
    
    async def _get_linkedin_profile(self, access_token: str) -> Dict[str, Any]:
        """Get LinkedIn profile information"""
        headers = {"Authorization": f"Bearer {access_token}"}
        
        async with httpx.AsyncClient() as client:
            try:
                # Get basic profile
                profile_response = await client.get(
                    "https://api.linkedin.com/v2/people/~",
                    headers=headers
                )
                profile_response.raise_for_status()
                profile_data = profile_response.json()
                
                # Try to get email if scope permits
                try:
                    email_response = await client.get(
                        "https://api.linkedin.com/v2/emailAddress?q=members&projection=(elements*(handle~))",
                        headers=headers
                    )
                    if email_response.status_code == 200:
                        email_data = email_response.json()
                        if email_data.get("elements") and len(email_data["elements"]) > 0:
                            profile_data["email"] = email_data["elements"][0].get("handle~", {}).get("emailAddress")
                except:
                    pass  # Email scope may not be granted
                
                return profile_data
                
            except Exception as e:
                logger.error(f"Failed to get LinkedIn profile: {e}")
                return {}
    
    async def _store_linkedin_connection(self, admin_email: str, token_data: Dict[str, Any], 
                                       requested_scopes: List[str], profile_data: Dict[str, Any]):
        """Store LinkedIn connection with permissions"""
        # Encrypt tokens
        access_token = self._encrypt_token(token_data["access_token"])
        refresh_token = self._encrypt_token(token_data.get("refresh_token", "")) if token_data.get("refresh_token") else None
        
        # Calculate expiration time
        expires_in = token_data.get("expires_in", 5184000)  # LinkedIn default: 60 days
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        
        # Extract profile info
        linkedin_profile_id = profile_data.get("id")
        profile_name = None
        if profile_data.get("localizedFirstName") or profile_data.get("localizedLastName"):
            profile_name = f"{profile_data.get('localizedFirstName', '')} {profile_data.get('localizedLastName', '')}".strip()
        
        # Get granted scopes from token response or assume requested scopes were granted
        granted_scopes = token_data.get("scope", " ".join(requested_scopes))
        
        # Store connection
        query = """
            INSERT INTO linkedin_oauth_connections 
            (admin_email, linkedin_profile_id, linkedin_profile_name, access_token, refresh_token, 
             token_expires_at, granted_scopes, requested_scopes)
            VALUES (:admin_email, :profile_id, :profile_name, :access_token, :refresh_token, 
                    :expires_at, :granted_scopes, :requested_scopes)
            ON CONFLICT (admin_email) 
            DO UPDATE SET 
                linkedin_profile_id = EXCLUDED.linkedin_profile_id,
                linkedin_profile_name = EXCLUDED.linkedin_profile_name,
                access_token = EXCLUDED.access_token,
                refresh_token = EXCLUDED.refresh_token,
                token_expires_at = EXCLUDED.token_expires_at,
                granted_scopes = EXCLUDED.granted_scopes,
                requested_scopes = EXCLUDED.requested_scopes,
                is_active = true,
                updated_at = NOW()
        """
        
        await database.execute(query, {
            "admin_email": admin_email,
            "profile_id": linkedin_profile_id,
            "profile_name": profile_name,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_at": expires_at,
            "granted_scopes": granted_scopes,
            "requested_scopes": " ".join(requested_scopes)
        })
        
        logger.info(f"LinkedIn connection stored for admin: {admin_email} with scopes: {granted_scopes}")
    
    # Connection Management Methods
    
    async def get_linkedin_connection(self, admin_email: str) -> Optional[Dict[str, Any]]:
        """Get LinkedIn connection for admin user"""
        query = """
            SELECT linkedin_profile_id, linkedin_profile_name, access_token, refresh_token, 
                   token_expires_at, granted_scopes, requested_scopes, last_sync_at, is_active
            FROM linkedin_oauth_connections 
            WHERE admin_email = :admin_email AND is_active = true
        """
        
        result = await database.fetch_one(query, {"admin_email": admin_email})
        if not result:
            return None
        
        try:
            connection = {
                "linkedin_profile_id": result["linkedin_profile_id"],
                "linkedin_profile_name": result["linkedin_profile_name"],
                "access_token": self._decrypt_token(result["access_token"]),
                "refresh_token": self._decrypt_token(result["refresh_token"]) if result["refresh_token"] else None,
                "expires_at": result["token_expires_at"],
                "granted_scopes": result["granted_scopes"].split() if result["granted_scopes"] else [],
                "requested_scopes": result["requested_scopes"].split() if result["requested_scopes"] else [],
                "last_sync_at": result["last_sync_at"],
                "is_active": result["is_active"]
            }
            
            # Check if token needs refresh
            if connection["expires_at"] and datetime.utcnow() >= connection["expires_at"]:
                if connection["refresh_token"]:
                    logger.info(f"Refreshing LinkedIn token for {admin_email}")
                    await self._refresh_linkedin_token(admin_email, connection["refresh_token"])
                    return await self.get_linkedin_connection(admin_email)
                else:
                    logger.warning(f"LinkedIn token expired for {admin_email} and no refresh token available")
                    return None
            
            return connection
            
        except Exception as e:
            logger.error(f"Failed to decrypt LinkedIn connection for {admin_email}: {e}")
            return None
    
    async def _refresh_linkedin_token(self, admin_email: str, refresh_token: str):
        """Refresh LinkedIn access token using refresh token"""
        config = await self.get_oauth_app_config()
        if not config:
            raise TTWOAuthManagerError("LinkedIn OAuth app not configured")
        
        token_data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": config["client_id"],
            "client_secret": config["client_secret"],
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    "https://www.linkedin.com/oauth/v2/accessToken",
                    data=token_data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                response.raise_for_status()
                token_response = response.json()
                
                # Update stored tokens
                encrypted_access = self._encrypt_token(token_response["access_token"])
                encrypted_refresh = self._encrypt_token(token_response.get("refresh_token", refresh_token))
                expires_at = datetime.utcnow() + timedelta(seconds=token_response.get("expires_in", 5184000))
                
                query = """
                    UPDATE linkedin_oauth_connections 
                    SET access_token = :access_token, 
                        refresh_token = :refresh_token,
                        token_expires_at = :expires_at,
                        updated_at = NOW()
                    WHERE admin_email = :admin_email
                """
                
                await database.execute(query, {
                    "admin_email": admin_email,
                    "access_token": encrypted_access,
                    "refresh_token": encrypted_refresh,
                    "expires_at": expires_at
                })
                
                logger.info(f"LinkedIn token refreshed for {admin_email}")
                
            except Exception as e:
                logger.error(f"Failed to refresh LinkedIn token for {admin_email}: {e}")
                # Remove invalid connection
                await self.remove_linkedin_connection(admin_email)
                raise TTWOAuthManagerError(f"Failed to refresh LinkedIn token: {e}")
    
    async def remove_linkedin_connection(self, admin_email: str) -> bool:
        """Remove LinkedIn connection for admin user"""
        try:
            query = "UPDATE linkedin_oauth_connections SET is_active = false WHERE admin_email = :admin_email"
            await database.execute(query, {"admin_email": admin_email})
            logger.info(f"LinkedIn connection removed for {admin_email}")
            return True
        except Exception as e:
            logger.error(f"Failed to remove LinkedIn connection for {admin_email}: {e}")
            return False
    
    async def is_linkedin_connected(self, admin_email: str) -> bool:
        """Check if admin user has valid LinkedIn connection"""
        connection = await self.get_linkedin_connection(admin_email)
        return connection is not None and connection["is_active"]
    
    async def update_last_sync(self, admin_email: str):
        """Update last sync timestamp for admin user"""
        query = """
            UPDATE linkedin_oauth_connections 
            SET last_sync_at = NOW() 
            WHERE admin_email = :admin_email
        """
        await database.execute(query, {"admin_email": admin_email})

# Global instance
ttw_oauth_manager = TTWOAuthManager()
