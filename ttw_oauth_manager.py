# ttw_oauth_manager.py - Through-The-Web OAuth Management Service
import os
import json
import logging
import secrets
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
from database import database
from log_capture import add_log
import httpx

logger = logging.getLogger(__name__)

class TTWOAuthManagerError(Exception):
    """Custom exception for TTW OAuth Manager errors"""
    pass

class TTWOAuthManager:
    """
    Through-The-Web OAuth Management Service
    Complete self-contained OAuth implementation with plain text storage
    """
    
    def __init__(self):
        # Default redirect URI pattern (will be configurable)
        self.default_redirec            if result:
                return {
                    "app_name": result.get("app_name") or "",
                    "client_id": result.get("client_id") or "",
                    "redirect_uri": result.get("redirect_uri") or "",
                    "scopes": result.get("scopes") or "",
                    "configured_at": result.get("created_at"),
                    "updated_at": result.get("updated_at")
                }tern = "/admin/linkedin/callback"
    
    # OAuth App Configuration Methods
    
    async def is_oauth_app_configured(self) -> bool:
        """Check if LinkedIn OAuth app is configured"""
        query = "SELECT COUNT(*) FROM oauth_apps WHERE provider = 'linkedin'"
        result = await database.fetch_val(query)
        return result > 0
    
    async def get_oauth_app_config(self) -> Optional[Dict[str, Any]]:
        """Get active LinkedIn OAuth app configuration"""
        try:
            #add_log("DEBUG", "oauth_config_lookup", "Looking up LinkedIn OAuth configuration")
            
            query = """
                SELECT app_name, client_id, client_secret, redirect_uri, scopes, created_by, created_at, updated_at
                FROM oauth_apps 
                WHERE provider = 'linkedin'
                ORDER BY updated_at DESC
                LIMIT 1
            """
            result = await database.fetch_one(query)
            
            if not result:
                add_log("ERROR", "oauth_config_not_found", "No LinkedIn OAuth configuration found in database")
                return None
            
            add_log("INFO", "oauth_config_found", f"LinkedIn OAuth config found: app_name={result['app_name']}")
            
            return {
                "app_name": result["app_name"],
                "client_id": result["client_id"],
                "client_secret": result["client_secret"],
                "redirect_uri": result["redirect_uri"],
                "scopes": result["scopes"],  # Include scopes field
                "configured_by_email": result["created_by"],
                "created_at": result["created_at"],
                "updated_at": result["updated_at"]
            }
            
        except Exception as e:
            add_log("ERROR", "oauth_config_error", f"Error retrieving OAuth config: {str(e)}")
            logger.error(f"Failed to retrieve OAuth app config: {e}")
            return None
    
    async def configure_oauth_app(self, admin_email: str, app_config: Dict[str, str]) -> bool:
        """Configure LinkedIn OAuth app through admin interface"""
        try:
                        # Log the configuration attempt
            add_log("INFO", "linkedin_oauth_config", 
                    f"Admin {admin_email} configuring LinkedIn OAuth app: {app_config.get('app_name', 'LinkedIn OAuth App')}")
            
            # Store client secret in plain text
            client_secret = app_config["client_secret"]
            
            # First, deactivate any existing LinkedIn OAuth configs
            deactivate_query = """
                UPDATE oauth_apps 
                SET is_active = false 
                WHERE provider = 'linkedin'
            """
            await database.execute(deactivate_query)
            
            # Insert new LinkedIn OAuth configuration
            from database import PORTFOLIO_ID
            query = """
                INSERT INTO oauth_apps (portfolio_id, provider, app_name, 
                                      client_id, client_secret, redirect_uri, 
                                      scopes, created_by)
                VALUES (:portfolio_id, :provider, :app_name, :client_id, 
                       :client_secret, :redirect_uri, :scopes, :created_by)
            """
            
            await database.execute(query, {
                "portfolio_id": PORTFOLIO_ID,
                "provider": "linkedin",
                "app_name": app_config.get("app_name", "LinkedIn OAuth App"),
                "client_id": app_config["client_id"],
                "client_secret": client_secret,
                "redirect_uri": app_config["redirect_uri"],
                "scopes": ",".join(app_config.get("scopes", ["r_liteprofile", "r_emailaddress"])),
                "created_by": admin_email
            })
            
            # Log successful configuration
            add_log("INFO", "linkedin_oauth_config_success", 
                    f"LinkedIn OAuth app successfully configured by {admin_email}")
            
            logger.info(f"LinkedIn OAuth app configured by admin: {admin_email}")
            return True
            
        except Exception as e:
            # Log configuration failure
            add_log("ERROR", "linkedin_oauth_config_failed", 
                    f"Failed to configure LinkedIn OAuth app for {admin_email}: {str(e)}")
            
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
        try:
            # Log authorization URL generation attempt
            add_log("INFO", "linkedin_auth_url_generate",
                    f"Get LinkedIn auth URL for {admin_email}")

            config = await self.get_oauth_app_config()
            if not config:
                add_log("ERROR", "linkedin_auth_url_no_config",
                        f"LinkedIn OAuth not configured for {admin_email}")
                raise TTWOAuthManagerError("LinkedIn OAuth app not configured. Please configure it first.")

            # Debug: Log config details (without secrets)
            add_log("DEBUG", "linkedin_auth_url_config_check",
                    f"OAuth config found - client_id present: "
                    f"{bool(config.get('client_id'))}, "
                    f"redirect_uri: {config.get('redirect_uri', 'None')}")

            if not requested_scopes:
                requested_scopes = await self.get_default_scopes()

            # Generate secure state parameter
            state_data = {
                "admin_email": admin_email,
                "requested_scopes": requested_scopes,
                "timestamp": datetime.utcnow().isoformat(),
                "nonce": secrets.token_urlsafe(16)
            }
            state = json.dumps(state_data)

            # Build authorization URL
            import urllib.parse
            params = {
                "response_type": "code",
                "client_id": config["client_id"],
                "redirect_uri": config["redirect_uri"],
                "state": state,
                "scope": " ".join(requested_scopes)
            }

            # URL encode parameters properly
            encoded_params = [f"{k}={urllib.parse.quote_plus(str(v))}"
                              for k, v in params.items()]
            param_string = "&".join(encoded_params)
            auth_url = (f"https://www.linkedin.com/oauth/v2/authorization?"
                        f"{param_string}")

            # Log successful URL generation
            add_log("DEBUG", "linkedin_auth_url_success",
                    f"LinkedIn auth URL generated for {admin_email}, scopes: {requested_scopes}")

            logger.info(f"Generated LinkedIn auth URL for {admin_email} with scopes: {requested_scopes}")
            return auth_url, state

        except Exception as e:
            # Log URL generation failure
            add_log("ERROR", "linkedin_auth_url_failed",
                    f"Failed to generate LinkedIn auth URL: {str(e)}")
            raise
    
    def verify_linkedin_state(self, state: str) -> Dict[str, Any]:
        """Verify and extract data from LinkedIn OAuth state parameter"""
        try:
            state_data = json.loads(state)
            
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
        admin_email = state_data["admin_email"]
        
        try:
            # Log token exchange attempt
            add_log("INFO", "linkedin_token_exchange",
                    f"Exchanging LinkedIn auth code for tokens: {admin_email}")

            config = await self.get_oauth_app_config()
            if not config:
                add_log("ERROR", "linkedin_token_exchange_no_config",
                        f"LinkedIn OAuth not configured for token exchange: {admin_email}")
                raise TTWOAuthManagerError("LinkedIn OAuth app not configured")

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
                    
                    # Log the OAuth response details
                    add_log("INFO", "linkedin_token_exchange_response",
                            f"LinkedIn token exchange response: status {response.status_code}")
                    
                    response.raise_for_status()
                    token_response = response.json()
                    
                    # Log token response details (without sensitive data)
                    expires_in = token_response.get('expires_in', 'unknown')
                    scope = token_response.get('scope', 'none')
                    add_log("INFO", "linkedin_token_response_details",
                            f"LinkedIn token response: expires_in={expires_in}, scope={scope}")

                    # Log successful token exchange
                    add_log("INFO", "linkedin_token_exchange_success",
                            f"LinkedIn tokens obtained for {admin_email}")

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
                    add_log("ERROR", "linkedin_token_exchange_request_failed",
                            f"LinkedIn token exchange request failed: {str(e)}",
                            admin_email, "exchange_linkedin_code_for_tokens")
                    logger.error(f"LinkedIn token exchange request failed: {e}")
                    raise TTWOAuthManagerError(f"Failed to exchange code for tokens: {e}")
                    
                except httpx.HTTPStatusError as e:
                    add_log("ERROR", "linkedin_token_exchange_http_error",
                            f"LinkedIn token exchange HTTP error: {e.response.status_code}",
                            admin_email, "exchange_linkedin_code_for_tokens")
                    logger.error(f"LinkedIn token exchange HTTP error: {e.response.status_code} - {e.response.text}")
                    raise TTWOAuthManagerError(f"LinkedIn token exchange failed: {e.response.status_code}")

        except Exception as e:
            # Log any other failures
            add_log("ERROR", "linkedin_token_exchange_failed",
                    f"LinkedIn token exchange failed: {str(e)}",
                    admin_email, "exchange_linkedin_code_for_tokens")
            raise
    
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
        try:
            # Log connection storage attempt
            add_log("INFO", "linkedin_connection_store",
                    f"Storing LinkedIn connection for {admin_email}",
                    admin_email, "_store_linkedin_connection")

            # Encrypt tokens
            access_token = token_data["access_token"]
            refresh_token = token_data.get("refresh_token", "") if token_data.get("refresh_token") else None
            
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
            from database import PORTFOLIO_ID
            query = """
                INSERT INTO linkedin_oauth_connections 
                (portfolio_id, admin_email, linkedin_profile_id, 
                 linkedin_profile_name, access_token, refresh_token, 
                 token_expires_at, granted_scopes, requested_scopes)
                VALUES (:portfolio_id, :admin_email, :profile_id, :profile_name, 
                       :access_token, :refresh_token, :expires_at, 
                       :granted_scopes, :requested_scopes)
                ON CONFLICT (portfolio_id, admin_email) 
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
                "portfolio_id": PORTFOLIO_ID,
                "admin_email": admin_email,
                "profile_id": linkedin_profile_id,
                "profile_name": profile_name,
                "access_token": access_token,
                "refresh_token": refresh_token,
                "expires_at": expires_at,
                "granted_scopes": granted_scopes,
                "requested_scopes": " ".join(requested_scopes)
            })

            # Log successful storage
            add_log("INFO", "linkedin_connection_store_success",
                    f"LinkedIn connection stored for {admin_email}, scopes: {granted_scopes}",
                    admin_email, "_store_linkedin_connection")

            logger.info(f"LinkedIn connection stored for admin: {admin_email} with scopes: {granted_scopes}")

        except Exception as e:
            # Log storage failure
            add_log("ERROR", "linkedin_connection_store_failed",
                    f"Failed to store LinkedIn connection: {str(e)}",
                    admin_email, "_store_linkedin_connection")
            raise
    
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
                "access_token": result["access_token"],
                "refresh_token": result["refresh_token"] if result["refresh_token"] else None,
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
        # Log token refresh attempt
        add_log("INFO", "linkedin_token_refresh",
                f"Refreshing LinkedIn token for {admin_email}",
                admin_email, "_refresh_linkedin_token")

        config = await self.get_oauth_app_config()
        if not config:
            add_log("ERROR", "linkedin_token_refresh_failed",
                    f"LinkedIn OAuth app not configured for {admin_email}",
                    admin_email, "_refresh_linkedin_token")
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
                encrypted_access = token_response["access_token"]
                encrypted_refresh = token_response.get("refresh_token", refresh_token)
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

                # Log successful refresh
                add_log("INFO", "linkedin_token_refresh_success",
                        f"LinkedIn token successfully refreshed for {admin_email}",
                        admin_email, "_refresh_linkedin_token")
                
                logger.info(f"LinkedIn token refreshed for {admin_email}")
                
            except Exception as e:
                # Log refresh failure
                add_log("ERROR", "linkedin_token_refresh_failed",
                        f"Failed to refresh LinkedIn token: {str(e)}",
                        admin_email, "_refresh_linkedin_token")

                logger.error(f"Failed to refresh LinkedIn token for {admin_email}: {e}")
                # Remove invalid connection
                await self.remove_linkedin_connection(admin_email)
                raise TTWOAuthManagerError(f"Failed to refresh LinkedIn token: {e}")
    
    async def remove_linkedin_connection(self, admin_email: str) -> bool:
        """Remove LinkedIn connection for admin user"""
        try:
            # Log the connection removal attempt
            add_log("INFO", "linkedin_connection_remove",
                    f"Admin {admin_email} removing LinkedIn connection",
                    admin_email, "remove_linkedin_connection")

            query = """
                DELETE FROM linkedin_oauth_connections
                WHERE admin_email = :admin_email
            """
            await database.execute(query, {"admin_email": admin_email})

            # Log successful removal
            add_log("INFO", "linkedin_connection_remove_success",
                    f"LinkedIn connection successfully removed for {admin_email}",
                    admin_email, "remove_linkedin_connection")

            logger.info(f"LinkedIn connection removed for {admin_email}")
            return True

        except Exception as e:
            # Log removal failure
            add_log("ERROR", "linkedin_connection_remove_failed",
                    f"Failed to remove LinkedIn connection: {str(e)}",
                    admin_email, "remove_linkedin_connection")

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

    # Google OAuth Methods
    async def configure_google_oauth_app(self, admin_email: str, app_config: Dict[str, str]) -> bool:
        """Configure Google OAuth application settings"""
        try:
            # Get default portfolio ID
            from database import PORTFOLIO_ID
            portfolio_id = PORTFOLIO_ID
            
            # Get existing configuration for comparison
            existing_query = """
                SELECT app_name, client_id, client_secret, redirect_uri, scopes, updated_at
                FROM oauth_apps 
                WHERE portfolio_id = :portfolio_id AND provider = 'google'
            """
            existing_config = await database.fetch_one(existing_query, {"portfolio_id": portfolio_id})
            
            # Prepare new values
            new_app_name = app_config.get("app_name", "Google OAuth App")
            new_client_id = app_config["client_id"]
            new_client_secret = app_config["client_secret"]
            new_redirect_uri = app_config.get("redirect_uri", f"{app_config.get('base_url', '')}/auth/google/callback")
            new_scopes = ",".join(["email", "profile"])
            
            # Log the configuration attempt
            add_log("INFO", "google_oauth_config_start", 
                   f"Admin {admin_email} configuring Google OAuth app",
                   admin_email, "configure_google_oauth_app")
            
            # Log field changes
            new_values = {
                "app_name": new_app_name,
                "client_id": new_client_id,
                "client_secret": "[REDACTED]",
                "redirect_uri": new_redirect_uri,
                "scopes": new_scopes
            }
            
            if existing_config:
                old_values = {k: existing_config.get(k, "NULL") for k in new_values.keys()}
                old_values["client_secret"] = "[REDACTED]"
                for field, new_val in new_values.items():
                    if old_values[field] != new_val:
                        add_log("INFO", "google_oauth_field_change", 
                               f"{field}: '{old_values[field]}' -> '{new_val}' by {admin_email}",
                               admin_email, "configure_google_oauth_app")
            else:
                for field, value in new_values.items():
                    add_log("INFO", "google_oauth_field_new", 
                           f"{field} set to '{value}' by {admin_email}",
                           admin_email, "configure_google_oauth_app")
            
            # Insert or update Google OAuth configuration
            query = """
                INSERT INTO oauth_apps (portfolio_id, provider, app_name, client_id, client_secret, redirect_uri, scopes, created_by, is_active)
                VALUES (:portfolio_id, :provider, :app_name, :client_id, :client_secret, :redirect_uri, :scopes, :created_by, :is_active)
                ON CONFLICT (portfolio_id, provider) 
                DO UPDATE SET 
                    app_name = EXCLUDED.app_name,
                    client_id = EXCLUDED.client_id,
                    client_secret = EXCLUDED.client_secret,
                    redirect_uri = EXCLUDED.redirect_uri,
                    scopes = EXCLUDED.scopes,
                    created_by = EXCLUDED.created_by,
                    is_active = EXCLUDED.is_active,
                    updated_at = CURRENT_TIMESTAMP
            """
            
            await database.execute(query, {
                "portfolio_id": portfolio_id,
                "provider": "google",
                "app_name": new_app_name,
                "client_id": new_client_id,
                "client_secret": new_client_secret,
                "redirect_uri": new_redirect_uri,
                "scopes": new_scopes,
                "created_by": admin_email,
                "is_active": True
            })
            
            # Log successful configuration
            add_log("INFO", "google_oauth_config_success", 
                   f"Google OAuth app successfully configured by {admin_email}",
                   admin_email, "configure_google_oauth_app")
            
            logger.info(f"Google OAuth app configured by {admin_email}")
            return True
            
        except Exception as e:
            # Log configuration failure
            add_log("ERROR", "google_oauth_config_failed", 
                   f"Failed to configure Google OAuth app for {admin_email}: {str(e)}",
                   admin_email, "configure_google_oauth_app")
            
            logger.error(f"Failed to configure Google OAuth app: {e}")
            return False

    async def is_google_oauth_app_configured(self) -> bool:
        """Check if Google OAuth app is configured"""
        try:
            if not database.is_connected:
                await database.connect()
            
            query = """
                SELECT COUNT(*) as count
                FROM oauth_apps 
                WHERE provider = 'google' AND is_active = true
            """
            result = await database.fetch_one(query)
            return result["count"] > 0
        except Exception as e:
            logger.error(f"Database error checking OAuth config: {e}")
            return False

    async def get_google_oauth_app_config(self) -> Optional[Dict[str, Any]]:
        """Get Google OAuth app configuration (without secrets)"""
        try:
            query = """
                SELECT app_name, client_id, redirect_uri, scopes, created_at, updated_at
                FROM oauth_apps 
                WHERE provider = 'google'
                ORDER BY updated_at DESC
                LIMIT 1
            """
            result = await database.fetch_one(query)
            
            if result:
                return {
                    "app_name": result.get("app_name") or "",
                    "client_id": result.get("client_id") or "",
                    "redirect_uri": result.get("redirect_uri") or "",
                    "scopes": result.get("scopes") or "",
                    "configured_at": result.get("created_at"),
                    "updated_at": result.get("updated_at")
                }
            return None
        except Exception as e:
            logger.error(f"Database error getting OAuth config: {e}")
            return None

    async def get_google_oauth_credentials(self) -> Optional[Dict[str, str]]:
        """Get Google OAuth credentials including client secret"""
        try:
            query = """
                SELECT client_id, client_secret, redirect_uri
                FROM oauth_apps 
                WHERE provider = 'google'
                ORDER BY updated_at DESC
                LIMIT 1
            """
            result = await database.fetch_one(query)
            
            if result:
                return {
                    "client_id": result.get("client_id") or "",
                    "client_secret": result.get("client_secret") or "",
                    "redirect_uri": result.get("redirect_uri") or ""
                }
            return None
        except Exception as e:
            logger.error(f"Database error getting OAuth credentials: {e}")
            return None

    async def remove_linkedin_oauth_app(self, admin_email: str) -> bool:
        """Remove LinkedIn OAuth app configuration"""
        try:
            # Log the removal attempt
            add_log("INFO", "linkedin_oauth_remove",
                    f"Admin {admin_email} removing LinkedIn OAuth app config",
                    admin_email, "remove_linkedin_oauth_app")

            query = """
                DELETE FROM oauth_apps
                WHERE provider = 'linkedin'
            """
            await database.execute(query)

            # Log successful removal
            add_log("INFO", "linkedin_oauth_remove_success",
                    f"LinkedIn OAuth app successfully removed by {admin_email}",
                    admin_email, "remove_linkedin_oauth_app")

            logger.info(f"LinkedIn OAuth app removed by {admin_email}")
            return True

        except Exception as e:
            # Log removal failure
            add_log("ERROR", "linkedin_oauth_remove_failed",
                    f"Failed to remove LinkedIn OAuth app: {str(e)}",
                    admin_email, "remove_linkedin_oauth_app")

            logger.error(f"Failed to remove LinkedIn OAuth app: {e}")
            return False

    async def remove_google_oauth_app(self, admin_email: str) -> bool:
        """Remove Google OAuth app configuration"""
        try:
            # Log the removal attempt
            add_log("INFO", "google_oauth_remove",
                    f"Admin {admin_email} removing Google OAuth app config",
                    admin_email, "remove_google_oauth_app")

            query = """
                DELETE FROM oauth_apps
                WHERE provider = 'google'
            """
            await database.execute(query)

            # Log successful removal
            add_log("INFO", "google_oauth_remove_success",
                    f"Google OAuth app successfully removed by {admin_email}",
                    admin_email, "remove_google_oauth_app")

            logger.info(f"Google OAuth app removed by {admin_email}")
            return True

        except Exception as e:
            # Log removal failure
            add_log("ERROR", "google_oauth_remove_failed",
                    f"Failed to remove Google OAuth app: {str(e)}",
                    admin_email, "remove_google_oauth_app")

            logger.error(f"Failed to remove Google OAuth app: {e}")
            return False

    # LinkedIn OAuth methods (mirror Google implementation)
    
    async def configure_linkedin_oauth_app(self, admin_email: str, app_config: Dict[str, str]) -> bool:
        """Configure LinkedIn OAuth application settings"""
        try:
            # Get default portfolio ID
            from database import PORTFOLIO_ID
            
            # Get existing configuration for comparison
            existing_query = """
                SELECT app_name, client_id, client_secret, redirect_uri, scopes, updated_at
                FROM oauth_apps 
                WHERE portfolio_id = :portfolio_id AND provider = 'linkedin' AND is_active = true
                ORDER BY updated_at DESC LIMIT 1
            """
            existing_config = await database.fetch_one(existing_query, {"portfolio_id": PORTFOLIO_ID})
            
            # Prepare new values
            new_app_name = app_config.get("app_name", "LinkedIn OAuth App")
            new_client_id = app_config["client_id"]
            new_client_secret = app_config["client_secret"]
            new_redirect_uri = app_config.get("redirect_uri", f"{app_config.get('base_url', '')}/auth/linkedin/callback")
            new_scopes = ["r_liteprofile", "r_emailaddress"]
            new_scopes_str = ",".join(new_scopes)
            
            # Log the configuration attempt
            add_log("INFO", "linkedin_oauth_config_start", 
                   f"Admin {admin_email} configuring LinkedIn OAuth app",
                   admin_email, "configure_linkedin_oauth_app")
            
            # Log field changes
            new_values = {
                "app_name": new_app_name,
                "client_id": new_client_id,
                "client_secret": "[REDACTED]",
                "redirect_uri": new_redirect_uri,
                "scopes": new_scopes_str
            }
            
            if existing_config:
                old_values = {k: existing_config.get(k, "NULL") for k in new_values.keys()}
                old_values["client_secret"] = "[REDACTED]"
                for field, new_val in new_values.items():
                    if old_values[field] != new_val:
                        add_log("INFO", "linkedin_oauth_field_change", 
                               f"{field}: '{old_values[field]}' -> '{new_val}' by {admin_email}",
                               admin_email, "configure_linkedin_oauth_app")
            else:
                for field, value in new_values.items():
                    add_log("INFO", "linkedin_oauth_field_new", 
                           f"{field} set to '{value}' by {admin_email}",
                           admin_email, "configure_linkedin_oauth_app")
            
            # Insert or update LinkedIn OAuth configuration
            query = """
                INSERT INTO oauth_apps (portfolio_id, provider, app_name, 
                                      client_id, client_secret, redirect_uri, 
                                      scopes, created_by, is_active)
                VALUES (:portfolio_id, :provider, :app_name, :client_id, 
                       :client_secret, :redirect_uri, :scopes, :created_by, :is_active)
                ON CONFLICT (portfolio_id, provider) 
                DO UPDATE SET 
                    app_name = EXCLUDED.app_name,
                    client_id = EXCLUDED.client_id,
                    client_secret = EXCLUDED.client_secret,
                    redirect_uri = EXCLUDED.redirect_uri,
                    scopes = EXCLUDED.scopes,
                    created_by = EXCLUDED.created_by,
                    is_active = EXCLUDED.is_active,
                    updated_at = CURRENT_TIMESTAMP
            """
            
            await database.execute(query, {
                "portfolio_id": PORTFOLIO_ID,
                "provider": "linkedin",
                "app_name": new_app_name,
                "client_id": new_client_id,
                "client_secret": new_client_secret,
                "redirect_uri": new_redirect_uri,
                "scopes": new_scopes_str,
                "created_by": admin_email
            })
            
            # Log successful configuration
            add_log("INFO", "linkedin_oauth_config_success", 
                   f"LinkedIn OAuth app successfully configured by {admin_email}",
                   admin_email, "configure_linkedin_oauth_app")
            
            logger.info(f"LinkedIn OAuth app configured by {admin_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to configure LinkedIn OAuth app: {e}")
            return False

    async def is_linkedin_oauth_app_configured(self) -> bool:
        """Check if LinkedIn OAuth app is configured"""
        query = """
            SELECT COUNT(*) as count
            FROM oauth_apps 
            WHERE provider = 'linkedin' AND is_active = true
        """
        result = await database.fetch_one(query)
        return result["count"] > 0

    async def get_linkedin_oauth_app_config(self) -> Optional[Dict[str, Any]]:
        """Get LinkedIn OAuth app configuration (without secrets)"""
        query = """
            SELECT app_name, client_id, redirect_uri, scopes, created_at, updated_at
            FROM oauth_apps 
            WHERE provider = 'linkedin' AND is_active = true
            ORDER BY updated_at DESC
            LIMIT 1
        """
        result = await database.fetch_one(query)
        
        if result:
            return {
                "app_name": result["app_name"],
                "client_id": result["client_id"],
                "redirect_uri": result["redirect_uri"],
                "scopes": result["scopes"],
                "configured_at": result["created_at"],
                "updated_at": result["updated_at"]
            }
        return None

    async def get_linkedin_oauth_credentials(self) -> Optional[Dict[str, str]]:
        """Get LinkedIn OAuth credentials including client secret"""
        query = """
            SELECT client_id, client_secret, redirect_uri
            FROM oauth_apps 
            WHERE provider = 'linkedin' AND is_active = true
            ORDER BY updated_at DESC
            LIMIT 1
        """
        result = await database.fetch_one(query)
        
        if result:
            return {
                "client_id": result["client_id"],
                "client_secret": result["client_secret"],
                "redirect_uri": result["redirect_uri"]
            }
        return None

# Global instance
ttw_oauth_manager = TTWOAuthManager()
