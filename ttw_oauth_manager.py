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
        self.default_redirect_pattern = "/admin/linkedin/callback"
    
    # OAuth App Configuration Methods
    
    async def is_oauth_app_configured(self) -> bool:
        """Check if LinkedIn OAuth app is configured"""
        from database import PORTFOLIO_ID
        portfolio_id = PORTFOLIO_ID
        query = "SELECT COUNT(*) FROM oauth_apps WHERE portfolio_id = :portfolio_id AND provider = 'linkedin'"
        result = await database.fetch_val(query, {"portfolio_id": portfolio_id})
        return result > 0
    
    async def get_oauth_app_config(self) -> Optional[Dict[str, Any]]:
        """Get active LinkedIn OAuth app configuration"""
        try:
            #add_log("DEBUG", "oauth_config_lookup", "Looking up LinkedIn OAuth configuration")
            
            from database import PORTFOLIO_ID
            portfolio_id = PORTFOLIO_ID
            
            query = """
                SELECT client_id, client_secret, redirect_uri, scopes, created_at, updated_at
                FROM oauth_apps 
                WHERE portfolio_id = :portfolio_id AND provider = 'linkedin'
                ORDER BY updated_at DESC
                LIMIT 1
            """
            params = {"portfolio_id": portfolio_id}
            add_log("DEBUG", "linkedin_oauth_config_query", f"Executing LinkedIn OAuth config query")
            add_log("DEBUG", "linkedin_oauth_config_params", f"Portfolio ID: {portfolio_id}")
            add_log("DEBUG", "linkedin_oauth_config_sql", f"SQL: SELECT client_id, client_secret, redirect_uri, scopes, created_at, updated_at FROM oauth_apps WHERE portfolio_id = '{portfolio_id}' AND provider = 'linkedin'")
            result = await database.fetch_one(query, params)
            
            if not result:
                add_log("ERROR", "oauth_config_not_found", "No LinkedIn OAuth configuration found in database")
                return None
            
            return {
                "client_id": result["client_id"],
                "client_secret": result["client_secret"],
                "redirect_uri": result["redirect_uri"],
                "scopes": result["scopes"],  # Include scopes field
                "created_at": result["created_at"],
                "updated_at": result["updated_at"]
            }
            
        except Exception as e:
            add_log("ERROR", "oauth_config_error", f"Error retrieving OAuth config: {str(e)}")
            logger.error(f"Failed to retrieve OAuth app config: {e}")
            return None
    
    async def configure_oauth_app(self, app_config: Dict[str, str]) -> bool:
        """Configure LinkedIn OAuth app through admin interface"""
        try:
                        # Log the configuration attempt
            add_log("INFO", "linkedin_oauth_config", 
                    "Configuring LinkedIn OAuth app")
            
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
                INSERT INTO oauth_apps (portfolio_id, provider, 
                                      client_id, client_secret, redirect_uri, 
                                      scopes)
                VALUES (:portfolio_id, :provider, :client_id, 
                       :client_secret, :redirect_uri, :scopes)
            """
            
            await database.execute(query, {
                "portfolio_id": PORTFOLIO_ID,
                "provider": "linkedin",
                "client_id": app_config["client_id"],
                "client_secret": client_secret,
                "redirect_uri": app_config["redirect_uri"],
                "scopes": ",".join(app_config.get("scopes", ["r_liteprofile", "r_emailaddress"]))
            })
            
            # Log successful configuration
            add_log("INFO", "linkedin_oauth_config_success", 
                    "LinkedIn OAuth app successfully configured")
            
            logger.info("LinkedIn OAuth app configured")
            return True
            
        except Exception as e:
            # Log configuration failure
            add_log("ERROR", "linkedin_oauth_config_failed", 
                    f"Failed to configure LinkedIn OAuth app: {str(e)}")
            
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
    
    async def get_linkedin_authorization_url(
        self, requested_scopes: List[str] = None
    ) -> Tuple[str, str]:
        """Generate LinkedIn OAuth authorization URL"""
        try:
            # Log authorization URL generation attempt
            add_log("INFO", "linkedin_auth_url_generate",
                    "Generating LinkedIn auth URL")

            config = await self.get_oauth_app_config()
            if not config:
                add_log("ERROR", "linkedin_auth_url_no_config",
                        "LinkedIn OAuth not configured")
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
                    f"LinkedIn auth URL generated, scopes: {requested_scopes}")

            logger.info(f"Generated LinkedIn auth URL with scopes: {requested_scopes}")
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
    
    async def exchange_linkedin_code_for_tokens(
        self, code: str, state_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Exchange LinkedIn authorization code for access tokens"""
        
        try:
            # Log token exchange attempt
            add_log("INFO", "linkedin_token_exchange",
                    "Exchanging LinkedIn auth code for tokens")

            config = await self.get_oauth_app_config()
            if not config:
                add_log("ERROR", "linkedin_token_exchange_no_config",
                        "LinkedIn OAuth not configured for token exchange")
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
                            "LinkedIn tokens obtained")

                    # Get user profile to extract granted scopes and profile info
                    profile_data = await self._get_linkedin_profile(
                        token_response["access_token"])

                    # Store connection with granted permissions
                    await self._store_linkedin_connection(
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
                            f"LinkedIn token exchange request failed: {str(e)}")
                    logger.error(f"LinkedIn token exchange request failed: {e}")
                    raise TTWOAuthManagerError(f"Failed to exchange code for tokens: {e}")
                    
                except httpx.HTTPStatusError as e:
                    add_log("ERROR", "linkedin_token_exchange_http_error",
                            f"LinkedIn token exchange HTTP error: {e.response.status_code}")
                    logger.error(f"LinkedIn token exchange HTTP error: {e.response.status_code}")
                    raise TTWOAuthManagerError(f"LinkedIn token exchange failed: {e.response.status_code}")

        except Exception as e:
            # Log any other failures
            add_log("ERROR", "linkedin_token_exchange_failed",
                    f"LinkedIn token exchange failed: {str(e)}")
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
    
    async def _store_linkedin_connection(
        self, token_data: Dict[str, Any], 
        requested_scopes: List[str], profile_data: Dict[str, Any]
    ):
        """Store LinkedIn connection with permissions"""
        try:
            # Log connection storage attempt
            add_log("INFO", "linkedin_connection_store",
                    "Storing LinkedIn connection")

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
                (portfolio_id,  linkedin_profile_id, 
                 linkedin_profile_name, access_token, refresh_token, 
                 token_expires_at, granted_scopes, requested_scopes)
                VALUES (:portfolio_id, : :profile_id, :profile_name, 
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
                "system": "system",  # Placeholder until schema updated
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
                    f"LinkedIn connection stored, scopes: {granted_scopes}")

            logger.info(f"LinkedIn connection stored with scopes: {granted_scopes}")

        except Exception as e:
            # Log storage failure
            add_log("ERROR", "linkedin_connection_store_failed",
                    f"Failed to store LinkedIn connection: {str(e)}")
            raise
    
    # Connection Management Methods
    
    async def get_linkedin_connection(self) -> Optional[Dict[str, Any]]:
        """Get LinkedIn connection for current portfolio"""
        from database import PORTFOLIO_ID
        query = """
            SELECT linkedin_profile_id, linkedin_profile_name, access_token, refresh_token, 
                   token_expires_at, granted_scopes, requested_scopes, last_sync_at, is_active
            FROM linkedin_oauth_connections 
            WHERE portfolio_id = :portfolio_id AND is_active = true
        """
        
        result = await database.fetch_one(query, {"portfolio_id": PORTFOLIO_ID})
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
                    logger.info("Refreshing LinkedIn token")
                    await self._refresh_linkedin_token(connection["refresh_token"])
                    return await self.get_linkedin_connection()
                else:
                    logger.warning("LinkedIn token expired and no refresh token available")
                    return None
            
            return connection
            
        except Exception as e:
            logger.error(f"Failed to decrypt LinkedIn connection: {e}")
            return None
    
    async def _refresh_linkedin_token(self, refresh_token: str):
        """Refresh LinkedIn access token using refresh token"""
        # Log token refresh attempt
        add_log("INFO", "linkedin_token_refresh",
                "Refreshing LinkedIn token")

        config = await self.get_oauth_app_config()
        if not config:
            add_log("ERROR", "linkedin_token_refresh_failed",
                    "LinkedIn OAuth app not configured")
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
                
                from database import PORTFOLIO_ID
                query = """
                    UPDATE linkedin_oauth_connections 
                    SET access_token = :access_token, 
                        refresh_token = :refresh_token,
                        token_expires_at = :expires_at,
                        updated_at = NOW()
                    WHERE portfolio_id = :portfolio_id
                """
                
                await database.execute(query, {
                    "portfolio_id": PORTFOLIO_ID,
                    "access_token": encrypted_access,
                    "refresh_token": encrypted_refresh,
                    "expires_at": expires_at
                })

                # Log successful refresh
                add_log("INFO", "linkedin_token_refresh_success",
                        "LinkedIn token successfully refreshed")
                
                logger.info("LinkedIn token refreshed")
                
            except Exception as e:
                # Log refresh failure
                add_log("ERROR", "linkedin_token_refresh_failed",
                        f"Failed to refresh LinkedIn token: {str(e)}")

                logger.error("Failed to refresh LinkedIn token")
                # Remove invalid connection
                await self.remove_linkedin_connection()
                raise TTWOAuthManagerError("Failed to refresh LinkedIn token")
    
    async def remove_linkedin_connection(self) -> bool:
        """Remove LinkedIn connection for current portfolio"""
        try:
            # Log the connection removal attempt
            add_log("INFO", "linkedin_connection_remove",
                    "Removing LinkedIn connection")

            from database import PORTFOLIO_ID
            query = """
                DELETE FROM linkedin_oauth_connections
                WHERE portfolio_id = :portfolio_id
            """
            await database.execute(query, {"portfolio_id": PORTFOLIO_ID})

            # Log successful removal
            add_log("INFO", "linkedin_connection_remove_success",
                    "LinkedIn connection successfully removed")

            logger.info("LinkedIn connection removed")
            return True

        except Exception as e:
            # Log removal failure
            add_log("ERROR", "linkedin_connection_remove_failed",
                    f"Failed to remove LinkedIn connection: {str(e)}")

            logger.error(f"Failed to remove LinkedIn connection: {e}")
            return False
    
    async def is_linkedin_connected(self) -> bool:
        """Check if current portfolio has valid LinkedIn connection"""
        connection = await self.get_linkedin_connection()
        return connection is not None and connection["is_active"]
    
    async def update_last_sync(self):
        """Update last sync timestamp for current portfolio"""
        from database import PORTFOLIO_ID
        query = """
            UPDATE linkedin_oauth_connections
            SET last_sync_at = NOW()
            WHERE portfolio_id = :portfolio_id
        """
        await database.execute(query, {"portfolio_id": PORTFOLIO_ID})

    # Google OAuth Methods
    async def configure_google_oauth_app(self, app_config: Dict[str, str]) -> bool:
        """Configure Google OAuth application settings"""
        try:
            # Get default portfolio ID
            from database import PORTFOLIO_ID
            portfolio_id = PORTFOLIO_ID
            
            # Get existing configuration for comparison
            existing_query = """
                SELECT client_id, client_secret, redirect_uri, scopes, updated_at
                FROM oauth_apps 
                WHERE portfolio_id = :portfolio_id AND provider = 'google'
            """
            existing_config = await database.fetch_one(existing_query, {"portfolio_id": portfolio_id})
            
            # Prepare new values
            new_client_id = app_config.get("client_id", "")
            new_client_secret = app_config.get("client_secret", "")
            new_redirect_uri = app_config.get("redirect_uri", "")
            new_scopes = ",".join(["email", "profile"])
            
            # Log the configuration attempt
            add_log("INFO", "Configuring Google OAuth app", "google_oauth_config_start")
            
            # Log field changes
            new_values = {
                "client_id": new_client_id,
                "client_secret": "[REDACTED]",
                "redirect_uri": new_redirect_uri,
                "scopes": new_scopes
            }
            
            if existing_config:
                old_values = {k: existing_config[k] or "" for k in new_values.keys()}
                old_values["client_secret"] = "[REDACTED]"
                for field, new_val in new_values.items():
                    old_val = old_values[field]
                    # Handle empty strings and NULL values consistently
                    if (old_val or "") != (new_val or ""):
                        add_log("INFO", f"{field}: '{old_val}' -> '{new_val}'", "google_oauth_field_change")
            else:
                for field, value in new_values.items():
                    add_log("INFO", f"{field} set to '{value}'", "google_oauth_field_new")
            
            # Insert or update Google OAuth configuration
            query = """
                INSERT INTO oauth_apps (portfolio_id, provider, client_id, client_secret, redirect_uri, scopes, is_active)
                VALUES (:portfolio_id, :provider, :client_id, :client_secret, :redirect_uri, :scopes, ::is_active)
                ON CONFLICT (portfolio_id, provider) 
                DO UPDATE SET 
                    client_id = EXCLUDED.client_id,
                    client_secret = EXCLUDED.client_secret,
                    redirect_uri = EXCLUDED.redirect_uri,
                    scopes = EXCLUDED.scopes,
                    is_active = EXCLUDED.is_active,
                    updated_at = CURRENT_TIMESTAMP
            """
            
            await database.execute(query, {
                "portfolio_id": portfolio_id,
                "provider": "google",
                "client_id": new_client_id,
                "client_secret": new_client_secret,
                "redirect_uri": new_redirect_uri,
                "scopes": new_scopes,
                "is_active": True
            })
            
            # Log successful configuration
            add_log("INFO", "Google OAuth app successfully configured", "google_oauth_config_success")
            
            logger.info("Google OAuth app configured")
            return True
            
        except Exception as e:
            # Log configuration failure
            add_log("ERROR", f"Failed to configure Google OAuth app: {str(e)}", "google_oauth_config_failed")
            
            logger.error(f"Failed to configure Google OAuth app: {e}")
            return False

    async def is_google_oauth_app_configured(self) -> bool:
        """Check if Google OAuth app is configured"""
        try:
            if not database.is_connected:
                await database.connect()
            
            from database import PORTFOLIO_ID
            portfolio_id = PORTFOLIO_ID
            
            query = """
                SELECT COUNT(*) as count
                FROM oauth_apps 
                WHERE portfolio_id = :portfolio_id AND provider = 'google'
            """
            params = {"portfolio_id": portfolio_id}
            logger.debug(f"Checking if Google OAuth is configured - query: {query}")
            logger.debug(f"Query parameters: {params}")
            logger.debug(f"Substituted query: SELECT COUNT(*) as count FROM oauth_apps WHERE portfolio_id = '{portfolio_id}' AND provider = 'google'")
            result = await database.fetch_one(query, params)
            return result["count"] > 0
        except Exception as e:
            logger.error(f"Database error checking OAuth config: {e}")
            return False

    async def get_google_oauth_app_config(self) -> Optional[Dict[str, Any]]:
        """Get Google OAuth app configuration (without secrets)"""
        try:
            from database import PORTFOLIO_ID
            portfolio_id = PORTFOLIO_ID
            
            query = """
                SELECT client_id, redirect_uri, scopes, created_at, updated_at
                FROM oauth_apps 
                WHERE portfolio_id = :portfolio_id AND provider = 'google'
                ORDER BY updated_at DESC
                LIMIT 1
            """
            params = {"portfolio_id": portfolio_id}
            add_log("DEBUG", "google_oauth_config_query", f"Executing Google OAuth config query")
            add_log("DEBUG", "google_oauth_config_params", f"Portfolio ID: {portfolio_id}")
            add_log("DEBUG", "google_oauth_config_sql", f"SQL: SELECT client_id, redirect_uri, scopes, created_at, updated_at FROM oauth_apps WHERE portfolio_id = '{portfolio_id}' AND provider = 'google'")
            result = await database.fetch_one(query, params)
            
            add_log("DEBUG", "google_oauth_config_result", f"Raw result: {result}")
            add_log("DEBUG", "google_oauth_config_result_type", f"Result type: {type(result)}")
            
            if result:
                add_log("DEBUG", "google_oauth_config_found", f"Found Google OAuth config")
                # Try different ways to access the data
                add_log("DEBUG", "google_oauth_config_items", f"Result items: {dict(result) if hasattr(result, 'items') else 'No items method'}")
                add_log("DEBUG", "google_oauth_config_keys", f"Result keys: {list(result.keys()) if hasattr(result, 'keys') else 'No keys method'}")
                
                config = {
                    "client_id": result["client_id"] if "client_id" in result else "",
                    "redirect_uri": result["redirect_uri"] if "redirect_uri" in result else "",
                    "scopes": result["scopes"] if "scopes" in result else "",
                    "configured_at": result["created_at"] if "created_at" in result else None,
                    "updated_at": result["updated_at"] if "updated_at" in result else None
                }
                add_log("DEBUG", "google_oauth_config_final", f"Final config: {config}")
                return config
            
            add_log("DEBUG", "google_oauth_config_none", "No Google OAuth config found")
            return None
        except Exception as e:
            logger.error(f"Database error getting OAuth config: {e}")
            return None

    async def get_google_oauth_credentials(self) -> Optional[Dict[str, str]]:
        """Get Google OAuth credentials including client secret"""
        try:
            from database import PORTFOLIO_ID
            portfolio_id = PORTFOLIO_ID
            
            query = """
                SELECT client_id, client_secret, redirect_uri
                FROM oauth_apps 
                WHERE portfolio_id = :portfolio_id AND provider = 'google'
                ORDER BY updated_at DESC
                LIMIT 1
            """
            params = {"portfolio_id": portfolio_id}
            add_log("DEBUG", "google_oauth_credentials_query", f"Executing Google OAuth credentials query during startup")
            add_log("DEBUG", "google_oauth_credentials_params", f"Portfolio ID: {portfolio_id}")
            add_log("DEBUG", "google_oauth_credentials_sql", f"SQL: SELECT client_id, client_secret, redirect_uri FROM oauth_apps WHERE portfolio_id = '{portfolio_id}' AND provider = 'google'")
            result = await database.fetch_one(query, params)

            add_log("DEBUG", "google_oauth_creds_result", f"Credentials raw result: {result}")
            
            if result:
                add_log("INFO", "google_oauth_credentials_found", f"Found Google OAuth credentials")
                credentials = {
                    "client_id": result["client_id"] if "client_id" in result else "",
                    "client_secret": result["client_secret"] if "client_secret" in result else "",
                    "redirect_uri": result["redirect_uri"] if "redirect_uri" in result else ""
                }
                add_log("DEBUG", "google_oauth_creds_final", f"Final credentials: {credentials}")
                return credentials
            else:
                add_log("WARNING", "google_oauth_credentials_missing", f"No Google OAuth credentials found")
            return None
        except Exception as e:
            add_log("ERROR", "database_error_oauth_credentials", f"Database error getting OAuth credentials: {str(e)}")
            return None

    async def remove_linkedin_oauth_app(self) -> bool:
        """Remove LinkedIn OAuth app configuration"""
        try:
            # Log the removal attempt
            add_log("INFO", "linkedin_oauth_remove",
                    "System",
                     "remove_linkedin_oauth_app")

            query = """
                DELETE FROM oauth_apps
                WHERE provider = 'linkedin'
            """
            await database.execute(query)

            # Log successful removal
            add_log("INFO", "linkedin_oauth_remove_success",
                    "System",
                     "remove_linkedin_oauth_app")

            logger.info("System")
            return True

        except Exception as e:
            # Log removal failure
            add_log("ERROR", "linkedin_oauth_remove_failed",
                    f"Failed to remove LinkedIn OAuth app: {str(e)}",
                     "remove_linkedin_oauth_app")

            logger.error(f"Failed to remove LinkedIn OAuth app: {e}")
            return False

    async def remove_google_oauth_app(self) -> bool:
        """Remove Google OAuth app configuration"""
        try:
            # Log the removal attempt
            add_log("INFO", "Removing Google OAuth app config", 
                    "google_oauth_remove")

            query = """
                DELETE FROM oauth_apps
                WHERE provider = 'google'
            """
            await database.execute(query)

            # Log successful removal
            add_log("INFO", "Google OAuth app successfully removed", "google_oauth_remove_success")

            logger.info("Google OAuth app removed")
            return True

        except Exception as e:
            # Log removal failure
            add_log("ERROR", f"Failed to remove Google OAuth app: {str(e)}", "google_oauth_remove_failed")

            logger.error(f"Failed to remove Google OAuth app: {e}")
            return False

    # LinkedIn OAuth methods (mirror Google implementation)
    
    async def configure_linkedin_oauth_app(self, app_config: Dict[str, str]) -> bool:
        """Configure LinkedIn OAuth application settings"""
        try:
            # Get default portfolio ID
            from database import PORTFOLIO_ID
            
            # Get existing configuration for comparison
            existing_query = """
                SELECT client_id, client_secret, redirect_uri, scopes, updated_at
                FROM oauth_apps 
                WHERE portfolio_id = :portfolio_id AND provider = 'linkedin'
                ORDER BY updated_at DESC LIMIT 1
            """
            existing_config = await database.fetch_one(existing_query, {"portfolio_id": PORTFOLIO_ID})
            
            # Prepare new values
            new_client_id = app_config.get("client_id", "")
            new_client_secret = app_config.get("client_secret", "")
            new_redirect_uri = app_config.get("redirect_uri", f"{app_config.get('base_url', '')}/auth/linkedin/callback")
            new_scopes = ["r_liteprofile", "r_emailaddress"]
            new_scopes_str = ",".join(new_scopes)
            
            # Log the configuration attempt
            add_log("INFO", "linkedin_oauth_config_start", 
                   "System",
                    "configure_linkedin_oauth_app")
            
            # Log field changes
            new_values = {
                "client_id": new_client_id,
                "client_secret": "[REDACTED]",
                "redirect_uri": new_redirect_uri,
                "scopes": new_scopes_str
            }
            
            if existing_config:
                old_values = {k: existing_config.get(k) or "" for k in new_values.keys()}
                old_values["client_secret"] = "[REDACTED]"
                for field, new_val in new_values.items():
                    old_val = old_values[field]
                    # Handle empty strings and NULL values consistently
                    if (old_val or "") != (new_val or ""):
                        add_log("INFO", "linkedin_oauth_field_change", 
                               "System",
                                "configure_linkedin_oauth_app")
            else:
                for field, value in new_values.items():
                    add_log("INFO", "linkedin_oauth_field_new", 
                           "System",
                            "configure_linkedin_oauth_app")
            
            # Insert or update LinkedIn OAuth configuration
            query = """
                INSERT INTO oauth_apps (portfolio_id, provider, 
                                      client_id, client_secret, redirect_uri, 
                                      scopes, is_active)
                VALUES (:portfolio_id, :provider, :client_id, 
                       :client_secret, :redirect_uri, :scopes, ::is_active)
                ON CONFLICT (portfolio_id, provider) 
                DO UPDATE SET 
                    client_id = EXCLUDED.client_id,
                    client_secret = EXCLUDED.client_secret,
                    redirect_uri = EXCLUDED.redirect_uri,
                    scopes = EXCLUDED.scopes,
                    is_active = EXCLUDED.is_active,
                    updated_at = CURRENT_TIMESTAMP
            """
            
            await database.execute(query, {
                "portfolio_id": PORTFOLIO_ID,
                "provider": "linkedin",
                "client_id": new_client_id,
                "client_secret": new_client_secret,
                "redirect_uri": new_redirect_uri,
                "scopes": new_scopes_str,
                "is_active": True
            })
            
            # Log successful configuration
            add_log("INFO", "linkedin_oauth_config_success", 
                   "System",
                    "configure_linkedin_oauth_app")
            
            logger.info("System")
            return True
            
        except Exception as e:
            logger.error(f"Failed to configure LinkedIn OAuth app: {e}")
            return False

    async def is_linkedin_oauth_app_configured(self) -> bool:
        """Check if LinkedIn OAuth app is configured"""
        query = """
            SELECT COUNT(*) as count
            FROM oauth_apps 
            WHERE provider = 'linkedin'
        """
        result = await database.fetch_one(query)
        return result["count"] > 0

    async def get_linkedin_oauth_app_config(self) -> Optional[Dict[str, Any]]:
        """Get LinkedIn OAuth app configuration (without secrets)"""
        from database import PORTFOLIO_ID
        portfolio_id = PORTFOLIO_ID
        query = """
            SELECT client_id, redirect_uri, scopes, created_at, updated_at
            FROM oauth_apps 
            WHERE portfolio_id = :portfolio_id AND provider = 'linkedin'
            ORDER BY updated_at DESC
            LIMIT 1
        """
        params = {"portfolio_id": portfolio_id}
        logger.debug(f"Executing LinkedIn OAuth app config query: {query}")
        logger.debug(f"Query parameters: {params}")
        logger.debug(f"Substituted query: SELECT client_id, redirect_uri, scopes, created_at, updated_at FROM oauth_apps WHERE portfolio_id = '{portfolio_id}' AND provider = 'linkedin' ORDER BY updated_at DESC LIMIT 1")
        result = await database.fetch_one(query, params)
        
        if result:
            return {
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
            WHERE provider = 'linkedin'
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
