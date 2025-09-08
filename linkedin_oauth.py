# linkedin_oauth.py - LinkedIn OAuth 2.0 Service
import os
import base64
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from database import database
import httpx
import secrets

logger = logging.getLogger(__name__)

class LinkedInOAuthError(Exception):
    """Custom exception for LinkedIn OAuth errors"""
    pass

class LinkedInOAuthService:
    """
    LinkedIn OAuth 2.0 Service
    Handles secure OAuth authentication and token management
    """
    
    def __init__(self):
        # LinkedIn OAuth configuration
        self.client_id = os.getenv("LINKEDIN_CLIENT_ID")
        self.client_secret = os.getenv("LINKEDIN_CLIENT_SECRET")
        self.redirect_uri = os.getenv("LINKEDIN_REDIRECT_URI", "http://localhost:8000/linkedin/oauth/callback")
        
        # Encryption key for storing tokens securely
        encryption_key = os.getenv("LINKEDIN_ENCRYPTION_KEY")
        if not encryption_key:
            # Generate a new key if none exists (should be set in production)
            encryption_key = Fernet.generate_key().decode()
            logger.warning("Generated new encryption key for LinkedIn tokens. Set LINKEDIN_ENCRYPTION_KEY in production.")
        
        try:
            self.cipher = Fernet(encryption_key.encode() if isinstance(encryption_key, str) else encryption_key)
        except Exception as e:
            logger.error(f"Failed to initialize encryption: {e}")
            raise LinkedInOAuthError("Invalid encryption key configuration")
    
    def is_configured(self) -> bool:
        """Check if LinkedIn OAuth is properly configured"""
        return bool(self.client_id and self.client_secret)
    
    def get_authorization_url(self, state: str = None) -> str:
        """Generate LinkedIn OAuth authorization URL"""
        if not self.is_configured():
            raise LinkedInOAuthError("LinkedIn OAuth not configured. Set LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET.")
        
        if not state:
            state = secrets.token_urlsafe(32)
        
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "state": state,
            "scope": "r_liteprofile r_emailaddress"  # Read-only access
        }
        
        param_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"https://www.linkedin.com/oauth/v2/authorization?{param_string}"
    
    async def exchange_code_for_tokens(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for access and refresh tokens"""
        if not self.is_configured():
            raise LinkedInOAuthError("LinkedIn OAuth not configured")
        
        # Add logging for token exchange
        from log_capture import add_log
        add_log(
            level="INFO",
            source="linkedin_oauth",
            message="LinkedIn OAuth token exchange initiated",
            module="linkedin_oauth",
            function="exchange_code_for_tokens",
            extra='{"action": "token_exchange_start"}'
        )
        
        token_data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    "https://www.linkedin.com/oauth/v2/accessToken",
                    data=token_data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                response.raise_for_status()
                result = response.json()
                
                # Log successful token exchange
                add_log(
                    level="INFO",
                    source="linkedin_oauth",
                    message="LinkedIn OAuth token exchange successful",
                    module="linkedin_oauth",
                    function="exchange_code_for_tokens",
                    extra='{"action": "token_exchange_success"}'
                )
                
                return result
            except httpx.RequestError as e:
                logger.error(f"Token exchange request failed: {e}")
                add_log(
                    level="ERROR",
                    source="linkedin_oauth",
                    message=f"LinkedIn OAuth token exchange failed: {str(e)}",
                    module="linkedin_oauth",
                    function="exchange_code_for_tokens",
                    extra=f'{{"action": "token_exchange_failed", "error": "{str(e)}"}}'
                )
                raise LinkedInOAuthError(f"Failed to exchange code for tokens: {e}")
            except httpx.HTTPStatusError as e:
                logger.error(f"Token exchange HTTP error: {e.response.status_code} - {e.response.text}")
                add_log(
                    level="ERROR",
                    source="linkedin_oauth",
                    message=f"LinkedIn OAuth HTTP error: {e.response.status_code}",
                    module="linkedin_oauth",
                    function="exchange_code_for_tokens",
                    extra=f'{{"action": "token_exchange_http_error", "status_code": {e.response.status_code}}}'
                )
                raise LinkedInOAuthError(f"LinkedIn token exchange failed: {e.response.status_code}")
    
    async def get_user_profile(self, access_token: str) -> Dict[str, Any]:
        """Get LinkedIn user profile information"""
        headers = {"Authorization": f"Bearer {access_token}"}
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    "https://api.linkedin.com/v2/people/~?projection=(id,firstName,lastName,emailAddress)",
                    headers=headers
                )
                response.raise_for_status()
                return response.json()
            except httpx.RequestError as e:
                logger.error(f"Profile request failed: {e}")
                raise LinkedInOAuthError(f"Failed to get user profile: {e}")
            except httpx.HTTPStatusError as e:
                logger.error(f"Profile HTTP error: {e.response.status_code} - {e.response.text}")
                raise LinkedInOAuthError(f"LinkedIn profile request failed: {e.response.status_code}")
    
    def _encrypt_token(self, token: str) -> str:
        """Encrypt a token for secure storage"""
        return self.cipher.encrypt(token.encode()).decode()
    
    def _decrypt_token(self, encrypted_token: str) -> str:
        """Decrypt a token from storage"""
        return self.cipher.decrypt(encrypted_token.encode()).decode()
    
    async def store_credentials(self, portfolio_id: str, token_data: Dict[str, Any], 
                               linkedin_profile_id: str = None) -> Dict[str, Any]:
        """Store LinkedIn OAuth credentials securely in database"""
        try:
            # Calculate token expiration
            expires_in = token_data.get("expires_in", 3600)  # Default 1 hour
            expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
            
            # Encrypt tokens
            encrypted_access_token = self._encrypt_token(token_data["access_token"])
            encrypted_refresh_token = None
            if token_data.get("refresh_token"):
                encrypted_refresh_token = self._encrypt_token(token_data["refresh_token"])
            
            # Store in database (upsert)
            query = """
                INSERT INTO linkedin_oauth_credentials 
                (portfolio_id, access_token, refresh_token, token_expires_at, linkedin_profile_id, scope)
                VALUES (:portfolio_id, :access_token, :refresh_token, :expires_at, :profile_id, :scope)
                ON CONFLICT (portfolio_id) 
                DO UPDATE SET
                    access_token = EXCLUDED.access_token,
                    refresh_token = EXCLUDED.refresh_token,
                    token_expires_at = EXCLUDED.token_expires_at,
                    linkedin_profile_id = EXCLUDED.linkedin_profile_id,
                    scope = EXCLUDED.scope,
                    updated_at = NOW()
                RETURNING id, created_at, updated_at
            """
            
            result = await database.fetch_one(query, {
                "portfolio_id": portfolio_id,
                "access_token": encrypted_access_token,
                "refresh_token": encrypted_refresh_token,
                "expires_at": expires_at,
                "profile_id": linkedin_profile_id,
                "scope": token_data.get("scope", "r_liteprofile r_emailaddress")
            })
            
            logger.info(f"Stored LinkedIn credentials for admin: {portfolio_id}")
            return {
                "status": "success",
                "portfolio_id": portfolio_id,
                "expires_at": expires_at.isoformat(),
                "linkedin_profile_id": linkedin_profile_id
            }
            
        except Exception as e:
            logger.error(f"Failed to store LinkedIn credentials: {e}")
            raise LinkedInOAuthError(f"Failed to store credentials: {e}")
    
    async def get_credentials(self, portfolio_id: str) -> Optional[Dict[str, Any]]:
        """Get LinkedIn credentials for an admin user"""
        try:
            query = """
                SELECT access_token, refresh_token, token_expires_at, linkedin_profile_id, scope, updated_at
                FROM linkedin_oauth_credentials 
                WHERE portfolio_id = :portfolio_id
            """
            
            result = await database.fetch_one(query, {"portfolio_id": portfolio_id})
            if not result:
                return None
            
            # Decrypt tokens
            access_token = self._decrypt_token(result["access_token"])
            refresh_token = None
            if result["refresh_token"]:
                refresh_token = self._decrypt_token(result["refresh_token"])
            
            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "expires_at": result["token_expires_at"],
                "linkedin_profile_id": result["linkedin_profile_id"],
                "scope": result["scope"],
                "updated_at": result["updated_at"]
            }
            
        except Exception as e:
            logger.error(f"Failed to get LinkedIn credentials for {portfolio_id}: {e}")
            return None
    
    async def delete_credentials(self, portfolio_id: str) -> bool:
        """Delete LinkedIn credentials for an admin user"""
        try:
            query = "DELETE FROM linkedin_oauth_credentials WHERE portfolio_id = :portfolio_id"
            await database.execute(query, {"portfolio_id": portfolio_id})
            logger.info(f"Deleted LinkedIn credentials for admin: {portfolio_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete LinkedIn credentials for {portfolio_id}: {e}")
            return False
    
    async def is_token_valid(self, portfolio_id: str) -> bool:
        """Check if stored token is still valid"""
        credentials = await self.get_credentials(portfolio_id)
        if not credentials:
            return False
        
        # Check if token has expired
        if credentials["expires_at"] <= datetime.utcnow():
            return False
        
        return True
    
    async def get_oauth_status(self, portfolio_id: str) -> Dict[str, Any]:
        """Get LinkedIn OAuth status for an admin user"""
        credentials = await self.get_credentials(portfolio_id)
        is_valid = await self.is_token_valid(portfolio_id) if credentials else False
        
        return {
            "configured": self.is_configured(),
            "connected": bool(credentials),
            "token_valid": is_valid,
            "expires_at": credentials["expires_at"].isoformat() if credentials else None,
            "linkedin_profile_id": credentials.get("linkedin_profile_id") if credentials else None,
            "scope": credentials.get("scope") if credentials else None
        }

# Global instance
linkedin_oauth = LinkedInOAuthService()