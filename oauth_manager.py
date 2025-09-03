# oauth_manager.py - Unified OAuth Management Service
import os
import json
import logging
import secrets
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from database import database
import httpx

logger = logging.getLogger(__name__)

class OAuthManagerError(Exception):
    """Custom exception for OAuth Manager errors"""
    pass

class OAuthManager:
    """
    Unified OAuth Management Service
    Handles Google authentication and optional LinkedIn connection
    """
    
    def __init__(self):
        # LinkedIn OAuth configuration
        self.linkedin_client_id = os.getenv("LINKEDIN_CLIENT_ID")
        self.linkedin_client_secret = os.getenv("LINKEDIN_CLIENT_SECRET")
        self.linkedin_redirect_uri = os.getenv("LINKEDIN_REDIRECT_URI", "http://localhost:8000/admin/linkedin/callback")
        
        # Encryption key for storing tokens securely
        encryption_key = os.getenv("OAUTH_ENCRYPTION_KEY")
        if not encryption_key:
            # Generate a new key if none exists (should be set in production)
            encryption_key = Fernet.generate_key().decode()
            logger.warning("Generated new encryption key for OAuth tokens. Set OAUTH_ENCRYPTION_KEY in production.")
        
        try:
            self.cipher = Fernet(encryption_key.encode() if isinstance(encryption_key, str) else encryption_key)
        except Exception as e:
            logger.error(f"Failed to initialize encryption: {e}")
            raise OAuthManagerError("Invalid encryption key configuration")
    
    def _encrypt_token(self, token: str) -> str:
        """Encrypt a token for secure storage"""
        return self.cipher.encrypt(token.encode()).decode()
    
    def _decrypt_token(self, encrypted_token: str) -> str:
        """Decrypt a token for use"""
        return self.cipher.decrypt(encrypted_token.encode()).decode()
    
    # LinkedIn OAuth Methods
    
    def is_linkedin_configured(self) -> bool:
        """Check if LinkedIn OAuth is properly configured"""
        return bool(self.linkedin_client_id and self.linkedin_client_secret)
    
    def get_linkedin_authorization_url(self, admin_email: str) -> Tuple[str, str]:
        """Generate LinkedIn OAuth authorization URL with state parameter"""
        if not self.is_linkedin_configured():
            raise OAuthManagerError("LinkedIn OAuth not configured. Set LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET.")
        
        # Generate secure state parameter containing admin email
        state_data = {
            "admin_email": admin_email,
            "timestamp": datetime.utcnow().isoformat(),
            "nonce": secrets.token_urlsafe(16)
        }
        state = self._encrypt_token(json.dumps(state_data))
        
        params = {
            "response_type": "code",
            "client_id": self.linkedin_client_id,
            "redirect_uri": self.linkedin_redirect_uri,
            "state": state,
            "scope": "r_liteprofile r_emailaddress w_member_social"  # Read access + basic write for profile
        }
        
        param_string = "&".join([f"{k}={v}" for k, v in params.items()])
        auth_url = f"https://www.linkedin.com/oauth/v2/authorization?{param_string}"
        
        return auth_url, state
    
    def verify_linkedin_state(self, state: str) -> str:
        """Verify and extract admin email from LinkedIn OAuth state parameter"""
        try:
            state_data = json.loads(self._decrypt_token(state))
            
            # Verify timestamp (state should be used within 10 minutes)
            timestamp = datetime.fromisoformat(state_data["timestamp"])
            if datetime.utcnow() - timestamp > timedelta(minutes=10):
                raise OAuthManagerError("OAuth state expired")
            
            return state_data["admin_email"]
        except Exception as e:
            logger.error(f"Failed to verify LinkedIn state: {e}")
            raise OAuthManagerError("Invalid OAuth state parameter")
    
    async def exchange_linkedin_code_for_tokens(self, code: str, admin_email: str) -> Dict[str, Any]:
        """Exchange LinkedIn authorization code for access and refresh tokens"""
        if not self.is_linkedin_configured():
            raise OAuthManagerError("LinkedIn OAuth not configured")
        
        token_data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.linkedin_redirect_uri,
            "client_id": self.linkedin_client_id,
            "client_secret": self.linkedin_client_secret,
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
                
                # Store tokens in database
                await self._store_linkedin_tokens(admin_email, token_response)
                
                return token_response
                
            except httpx.RequestError as e:
                logger.error(f"LinkedIn token exchange request failed: {e}")
                raise OAuthManagerError(f"Failed to exchange code for tokens: {e}")
            except httpx.HTTPStatusError as e:
                logger.error(f"LinkedIn token exchange HTTP error: {e.response.status_code} - {e.response.text}")
                raise OAuthManagerError(f"LinkedIn token exchange failed: {e.response.status_code}")
    
    async def _store_linkedin_tokens(self, admin_email: str, token_data: Dict[str, Any]):
        """Store LinkedIn tokens securely in database"""
        access_token = self._encrypt_token(token_data["access_token"])
        refresh_token = self._encrypt_token(token_data.get("refresh_token", "")) if token_data.get("refresh_token") else None
        
        # Calculate expiration time
        expires_in = token_data.get("expires_in", 5184000)  # LinkedIn default: 60 days
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        
        # Get LinkedIn profile ID
        linkedin_profile_id = await self._get_linkedin_profile_id(token_data["access_token"])
        
        query = """
            INSERT INTO linkedin_oauth_credentials 
            (admin_email, access_token, refresh_token, token_expires_at, linkedin_profile_id, scope, updated_at)
            VALUES (:admin_email, :access_token, :refresh_token, :expires_at, :profile_id, :scope, NOW())
            ON CONFLICT (admin_email) 
            DO UPDATE SET 
                access_token = EXCLUDED.access_token,
                refresh_token = EXCLUDED.refresh_token,
                token_expires_at = EXCLUDED.token_expires_at,
                linkedin_profile_id = EXCLUDED.linkedin_profile_id,
                scope = EXCLUDED.scope,
                updated_at = NOW()
        """
        
        await database.execute(query, {
            "admin_email": admin_email,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_at": expires_at,
            "profile_id": linkedin_profile_id,
            "scope": token_data.get("scope", "r_liteprofile r_emailaddress")
        })
        
        logger.info(f"LinkedIn tokens stored for admin: {admin_email}")
    
    async def _get_linkedin_profile_id(self, access_token: str) -> Optional[str]:
        """Get LinkedIn profile ID from access token"""
        headers = {"Authorization": f"Bearer {access_token}"}
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    "https://api.linkedin.com/v2/people/~",
                    headers=headers
                )
                response.raise_for_status()
                profile_data = response.json()
                return profile_data.get("id")
            except Exception as e:
                logger.warning(f"Failed to get LinkedIn profile ID: {e}")
                return None
    
    async def get_linkedin_credentials(self, admin_email: str) -> Optional[Dict[str, Any]]:
        """Get LinkedIn credentials for an admin user"""
        query = """
            SELECT access_token, refresh_token, token_expires_at, linkedin_profile_id, scope
            FROM linkedin_oauth_credentials 
            WHERE admin_email = :admin_email
        """
        
        result = await database.fetch_one(query, {"admin_email": admin_email})
        if not result:
            return None
        
        try:
            credentials = {
                "access_token": self._decrypt_token(result["access_token"]),
                "refresh_token": self._decrypt_token(result["refresh_token"]) if result["refresh_token"] else None,
                "expires_at": result["token_expires_at"],
                "linkedin_profile_id": result["linkedin_profile_id"],
                "scope": result["scope"]
            }
            
            # Check if token needs refresh
            if credentials["expires_at"] and datetime.utcnow() >= credentials["expires_at"]:
                if credentials["refresh_token"]:
                    logger.info(f"Refreshing LinkedIn token for {admin_email}")
                    await self._refresh_linkedin_token(admin_email, credentials["refresh_token"])
                    return await self.get_linkedin_credentials(admin_email)
                else:
                    logger.warning(f"LinkedIn token expired for {admin_email} and no refresh token available")
                    return None
            
            return credentials
        except Exception as e:
            logger.error(f"Failed to decrypt LinkedIn credentials for {admin_email}: {e}")
            return None
    
    async def _refresh_linkedin_token(self, admin_email: str, refresh_token: str):
        """Refresh LinkedIn access token using refresh token"""
        if not self.is_linkedin_configured():
            raise OAuthManagerError("LinkedIn OAuth not configured")
        
        token_data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self.linkedin_client_id,
            "client_secret": self.linkedin_client_secret,
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
                
                # Store refreshed tokens
                await self._store_linkedin_tokens(admin_email, token_response)
                
                logger.info(f"LinkedIn token refreshed for {admin_email}")
                
            except Exception as e:
                logger.error(f"Failed to refresh LinkedIn token for {admin_email}: {e}")
                # Remove invalid credentials
                await self.remove_linkedin_credentials(admin_email)
                raise OAuthManagerError(f"Failed to refresh LinkedIn token: {e}")
    
    async def remove_linkedin_credentials(self, admin_email: str):
        """Remove LinkedIn credentials for an admin user"""
        query = "DELETE FROM linkedin_oauth_credentials WHERE admin_email = :admin_email"
        await database.execute(query, {"admin_email": admin_email})
        logger.info(f"LinkedIn credentials removed for {admin_email}")
    
    async def is_linkedin_connected(self, admin_email: str) -> bool:
        """Check if admin user has valid LinkedIn credentials"""
        credentials = await self.get_linkedin_credentials(admin_email)
        return credentials is not None
    
    async def get_linkedin_profile_data(self, admin_email: str) -> Optional[Dict[str, Any]]:
        """Get LinkedIn profile data for admin user"""
        credentials = await self.get_linkedin_credentials(admin_email)
        if not credentials:
            return None
        
        headers = {"Authorization": f"Bearer {credentials['access_token']}"}
        
        async with httpx.AsyncClient() as client:
            try:
                # Get basic profile
                profile_response = await client.get(
                    "https://api.linkedin.com/v2/people/~",
                    headers=headers
                )
                profile_response.raise_for_status()
                
                # Get email address
                email_response = await client.get(
                    "https://api.linkedin.com/v2/emailAddress?q=members&projection=(elements*(handle~))",
                    headers=headers
                )
                email_response.raise_for_status()
                
                profile_data = profile_response.json()
                email_data = email_response.json()
                
                # Extract email
                email = None
                if email_data.get("elements") and len(email_data["elements"]) > 0:
                    email = email_data["elements"][0].get("handle~", {}).get("emailAddress")
                
                return {
                    "profile": profile_data,
                    "email": email
                }
                
            except Exception as e:
                logger.error(f"Failed to get LinkedIn profile data for {admin_email}: {e}")
                return None

# Global instance
oauth_manager = OAuthManager()
