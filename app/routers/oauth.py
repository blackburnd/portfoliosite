import os
import secrets
import httpx
from urllib.parse import urlencode

from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from jose import jwt, jwk
from jose.exceptions import JWTError

from auth import (
    is_authorized_user,
    create_access_token,
    require_admin_auth,
    SECRET_KEY,
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    AUTHORIZED_EMAILS
)
from log_capture import log_with_context
from ttw_oauth_manager import TTWOAuthManager

router = APIRouter()
templates = Jinja2Templates(directory="templates")

# Admin credentials from environment
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin")


# --- Google OAuth Authentication Routes ---

GOOGLE_DISCOVERY_URL = (
    "https://accounts.google.com/.well-known/openid-configuration"
)
GOOGLE_CERTS_URL = None  # Will be fetched from discovery


async def get_google_certs():
    """Fetch and cache Google's public keys for token verification."""
    global GOOGLE_CERTS_URL
    try:
        async with httpx.AsyncClient() as client:
            if not GOOGLE_CERTS_URL:
                discovery_response = await client.get(GOOGLE_DISCOVERY_URL)
                discovery_response.raise_for_status()
                GOOGLE_CERTS_URL = discovery_response.json()["jwks_uri"]

            certs_response = await client.get(GOOGLE_CERTS_URL)
            certs_response.raise_for_status()
            return certs_response.json()["keys"]
    except httpx.RequestError as e:
        log_with_context(
            "ERROR", "get_google_certs",
            f"Failed to fetch Google certs: {e}"
        )
        return None


@router.get("/auth/login")
async def auth_login(request: Request):
    """Initiate Google OAuth login via popup"""
    try:
        log_with_context(
            "INFO", "auth", "User initiated Google OAuth login process",
            request
        )

        ttw_manager = TTWOAuthManager()
        google_config = await ttw_manager.get_google_oauth_app_config()

        if not google_config:
            return JSONResponse({
                "status": "error",
                "error": "Google OAuth is not configured. "
                         "Please configure it first.",
                "redirect": "/admin/google/oauth"
            }, status_code=503)

        state = secrets.token_urlsafe(32)
        request.session['oauth_state'] = state

        scope = 'openid email profile'

        params = {
            "client_id": google_config['client_id'],
            "redirect_uri": google_config['redirect_uri'],
            "response_type": "code",
            "scope": scope,
            "state": state,
            "access_type": "offline",
            "prompt": "select_account"
        }

        auth_url = "https://accounts.google.com/o/oauth2/v2/auth?"
        auth_url += urlencode(params)

        # Create OAuth session record at the start of the workflow
        from database import create_oauth_session, get_portfolio_id
        
        await create_oauth_session(
            portfolio_id=get_portfolio_id(),
            state=state,
            scopes=scope,
            auth_url=auth_url,
            redirect_uri=google_config['redirect_uri']
        )

        log_with_context(
            "INFO", "auth", f"OAuth session created with state: {state}",
            request
        )

        return JSONResponse({"status": "success", "auth_url": auth_url})

    except Exception as e:
        log_with_context(
            "ERROR", "auth_login", f"OAuth login error: {str(e)}",
            request, exc_info=True
        )
        return JSONResponse({
            "status": "error",
            "error": "An unexpected authentication error occurred."
        }, status_code=500)


@router.get("/auth/callback")
async def auth_callback(request: Request):
    """Handle Google OAuth callback"""
    try:
        error = request.query_params.get('error')
        callback_state = request.query_params.get('state')
        
        # Update OAuth session with callback information
        from database import update_oauth_session_with_callback
        
        if error:
            log_with_context(
                "WARNING", "auth_callback", f"OAuth error received: {error}",
                request
            )
            if callback_state:
                await update_oauth_session_with_callback(
                    oauth_state=callback_state,
                    code=None,
                    error=error
                )
            # Redirect to admin login form as fallback for OAuth errors
            return RedirectResponse(
                url="/auth/admin-login?error=Google%20OAuth%20error:%20"
                    f"{error}",
                status_code=302
            )

        session_state = request.session.get('oauth_state')

        if not callback_state or callback_state != session_state:
            log_with_context(
                "ERROR", "auth_callback", "CSRF validation failed", request
            )
            if callback_state:
                await update_oauth_session_with_callback(
                    oauth_state=callback_state,
                    code=None,
                    error="CSRF validation failed"
                )
            return HTMLResponse(
                "<h1>Security Error</h1><p>CSRF validation failed.</p>",
                status_code=400
            )

        request.session.pop('oauth_state', None)

        code = request.query_params.get('code')
        if not code:
            await update_oauth_session_with_callback(
                oauth_state=callback_state,
                code=None,
                error="Authorization code not found"
            )
            return HTMLResponse(
                "<h1>Authentication Error</h1>"
                "<p>Authorization code not found.</p>",
                status_code=400
            )

        ttw_manager = TTWOAuthManager()
        google_config = await ttw_manager.get_google_oauth_credentials()
        if not google_config or not google_config.get('client_id'):
            await update_oauth_session_with_callback(
                oauth_state=callback_state,
                code=code,
                error="Google OAuth configuration missing"
            )
            raise HTTPException(
                status_code=503, detail="Google OAuth is not configured."
            )

        token_url = "https://oauth2.googleapis.com/token"
        token_data = {
            "code": code,
            "client_id": google_config['client_id'],
            "client_secret": google_config['client_secret'],
            "redirect_uri": google_config['redirect_uri'],
            "grant_type": "authorization_code"
        }

        async with httpx.AsyncClient() as client:
            token_response = await client.post(token_url, data=token_data)

        token_response.raise_for_status()
        token_payload = token_response.json()
        id_token = token_payload.get('id_token')

        # Verify the ID token
        keys = await get_google_certs()
        if not keys:
            await update_oauth_session_with_callback(
                oauth_state=callback_state,
                code=code,
                error="Could not retrieve Google's public keys"
            )
            raise HTTPException(
                status_code=500,
                detail="Could not retrieve Google's public keys."
            )

        # Re-fetch credentials just before use to ensure they are fresh
        ttw_manager = TTWOAuthManager()
        google_config = await ttw_manager.get_google_oauth_credentials()
        if not google_config or not google_config.get('client_id'):
            await update_oauth_session_with_callback(
                oauth_state=callback_state,
                code=code,
                error="Google OAuth configuration missing on token verification"
            )
            raise HTTPException(
                status_code=503, detail="Google OAuth is not configured."
            )

        try:
            log_with_context(
                "DEBUG", "auth_callback",
                f"About to verify ID token. Token length: "
                f"{len(id_token) if id_token else 0}", request
            )
            
            header = jwt.get_unverified_header(id_token)
            kid = header['kid']
            
            log_with_context(
                "DEBUG", "auth_callback",
                f"Token header: {header}, Looking for kid: {kid}", request
            )

            key = next((k for k in keys if k['kid'] == kid), None)
            if not key:
                available_kids = [k.get('kid') for k in keys]
                log_with_context(
                    "ERROR", "auth_callback",
                    f"Public key not found for kid: {kid}. "
                    f"Available kids: {available_kids}", request
                )
                raise JWTError("Public key not found for token.")

            public_key = jwk.construct(key)
            
            log_with_context(
                "DEBUG", "auth_callback",
                f"Attempting JWT decode with client_id: "
                f"{google_config['client_id']}", request
            )

            user_info = jwt.decode(
                id_token,
                public_key,
                algorithms=[header['alg']],
                audience=google_config['client_id'],
                issuer='https://accounts.google.com',
                options={"verify_at_hash": False}
            )
            email = user_info.get('email')
            
            log_with_context(
                "DEBUG", "auth_callback",
                f"Successfully decoded token for email: {email}", request
            )

        except JWTError as e:
            token_preview = id_token[:100] if id_token else 'None'
            log_with_context(
                "ERROR", "auth_callback",
                f"ID Token verification failed: {e}. "
                f"Token: {token_preview}...", request
            )
            await update_oauth_session_with_callback(
                oauth_state=callback_state,
                code=code,
                error=f"ID Token verification failed: {str(e)}"
            )
            # Redirect to admin login form as fallback
            return RedirectResponse(
                url="/auth/admin-login?error=Google%20OAuth%20failed."
                    "%20Please%20use%20admin%20login.",
                status_code=302
            )

        # Update OAuth session with user email from successful callback
        # Email is always from AUTHORIZED_EMAILS collection verified earlier
        await update_oauth_session_with_callback(
            oauth_state=callback_state,
            code=code,
            email=email
        )

        if not email or not is_authorized_user(email):
            log_with_context(
                "WARNING", "auth",
                f"Unauthorized login attempt by {email}", request
            )
            await update_oauth_session_with_callback(
                oauth_state=callback_state,
                code=code,
                error=f"Unauthorized user: {email}"
            )
            return HTMLResponse(
                f"<h1>Access Denied</h1>"
                f"<p>Email {email} is not authorized.</p>",
                status_code=403
            )

        # Complete the OAuth session with final token information
        from database import complete_oauth_session
        from datetime import datetime, timedelta

        expires_in = token_payload.get('expires_in', 3600)
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

        await complete_oauth_session(
            oauth_state=callback_state,
            access_token=token_payload['access_token'],
            refresh_token=token_payload.get('refresh_token'),
            expires_at=expires_at,
            scopes=token_payload.get('scope')
        )

        access_token = create_access_token(data={"sub": email})
        log_with_context(
            "INFO", "auth", f"Successful login by {email} - JWT created",
            request
        )

        response = HTMLResponse(f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Authentication Successful</title>
                <style>
                    body {{
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                        margin: 0;
                        padding: 0;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        height: 100vh;
                        color: white;
                    }}
                    .success-container {{
                        background: rgba(255, 255, 255, 0.95);
                        color: #333;
                        padding: 2rem;
                        border-radius: 12px;
                        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
                        text-align: center;
                        max-width: 400px;
                        width: 90%;
                    }}
                    .success-icon {{
                        font-size: 3rem;
                        color: #28a745;
                        margin-bottom: 1rem;
                    }}
                    .success-title {{
                        font-size: 1.5rem;
                        font-weight: 600;
                        margin-bottom: 0.5rem;
                        color: #28a745;
                    }}
                    .user-info {{
                        background: #f8f9fa;
                        padding: 1rem;
                        border-radius: 8px;
                        margin: 1rem 0;
                        border-left: 4px solid #28a745;
                    }}
                    .user-email {{
                        font-weight: 500;
                        color: #495057;
                    }}
                    .countdown {{
                        font-size: 0.9rem;
                        color: #6c757d;
                        margin-top: 1rem;
                    }}
                    .countdown-number {{
                        font-weight: bold;
                        color: #28a745;
                    }}
                    .spinner {{
                        border: 2px solid #f3f3f3;
                        border-top: 2px solid #28a745;
                        border-radius: 50%;
                        width: 20px;
                        height: 20px;
                        animation: spin 1s linear infinite;
                        display: inline-block;
                        margin-right: 8px;
                    }}
                    @keyframes spin {{
                        0% {{ transform: rotate(0deg); }}
                        100% {{ transform: rotate(360deg); }}
                    }}
                </style>
            </head>
            <body>
                <div class="success-container">
                    <div class="success-icon">✓</div>
                    <div class="success-title">Authentication Successful!</div>
                    <p>You have successfully logged in to Blackburn Systems portfolio.</p>
                    
                    <div class="user-info">
                        <div class="user-email">Logged in as: {email}</div>
                    </div>
                    
                    <div class="countdown">
                        <span class="spinner"></span>
                        This window will close automatically in <span class="countdown-number" id="countdown">3</span> seconds
                    </div>
                </div>
                
                <script>
                    let countdownValue = 3;
                    const countdownElement = document.getElementById('countdown');
                    
                    const countdownTimer = setInterval(() => {{
                        countdownValue--;
                        countdownElement.textContent = countdownValue;
                        
                        if (countdownValue <= 0) {{
                            clearInterval(countdownTimer);
                            closeWindow();
                        }}
                    }}, 1000);
                    
                    function closeWindow() {{
                        // Always try to send token to parent window if it exists
                        if (window.opener && !window.opener.closed) {{
                            try {{
                                window.opener.postMessage({{
                                    type: 'OAUTH_SUCCESS',
                                    token: '{access_token}',
                                    user: {{
                                        email: '{email}'
                                    }}
                                }}, window.location.origin);
                            }} catch (e) {{
                                console.log('Could not send message to parent:', e);
                            }}
                        }}
                        
                        // Set cookie regardless (for backup)
                        try {{
                            document.cookie = 'access_token={access_token}; path=/; max-age={int(ACCESS_TOKEN_EXPIRE_MINUTES * 60)}; SameSite=Lax' + (window.location.protocol === 'https:' ? '; Secure' : '');
                        }} catch (e) {{
                            console.log('Could not set cookie:', e);
                        }}
                        
                        // Always try to close the window
                        try {{
                            window.close();
                        }} catch (e) {{
                            console.log('Could not close window:', e);
                            // If we can't close (maybe not a popup), redirect as fallback
                            window.location.href = '/workadmin';
                        }}
                        
                        // Fallback: if window didn't close after a short delay, redirect
                        setTimeout(() => {{
                            if (!window.closed) {{
                                window.location.href = '/workadmin';
                            }}
                        }}, 500);
                    }}
                    
                    // Also allow manual closing by clicking anywhere
                    document.addEventListener('click', closeWindow);
                </script>
            </body>
            </html>
        """)

        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=os.getenv("ENV") == "production",
            samesite="lax",
            max_age=int(ACCESS_TOKEN_EXPIRE_MINUTES * 60)
        )
        return response

    except httpx.HTTPStatusError as e:
        error_details = e.response.text
        log_with_context(
            "ERROR", "auth_callback",
            f"HTTP error during token exchange: {e} - {error_details}",
            request, exc_info=True
        )
        return HTMLResponse(
            "<h1>Authentication Failed</h1>"
            f"<p>Error exchanging authorization code: {error_details}</p>",
            status_code=400
        )
    except Exception as e:
        log_with_context(
            "ERROR", "auth_callback", f"OAuth callback error: {str(e)}",
            request, exc_info=True
        )
        return HTMLResponse(
            "<h1>Authentication Failed</h1>"
            f"<p>An unexpected error occurred: {str(e)}</p>",
            status_code=500
        )


@router.get("/auth/logout")
async def logout(request: Request):
    """Log out the user by clearing the JWT cookie."""
    log_with_context("INFO", "auth", "User logged out", request)
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie(key="access_token")
    return response


@router.get("/auth/status")
async def auth_status(request: Request):
    """Get authentication status based on JWT cookie."""
    try:
        token = request.cookies.get("access_token")
        if not token:
            return JSONResponse({"authenticated": False})

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")

        if email and is_authorized_user(email):
            return JSONResponse({"authenticated": True, "email": email})
        return JSONResponse({"authenticated": False})
    except (jwt.JWTError, jwt.ExpiredSignatureError):
        return JSONResponse({"authenticated": False})

# --- Google OAuth Admin Endpoints ---


@router.get("/admin/google/oauth", response_class=HTMLResponse)
async def google_oauth_admin_page(
    request: Request,
    admin: dict = Depends(require_admin_auth)
):
    return templates.TemplateResponse("google_oauth_admin.html", {
        "request": request,
        "current_page": "google_oauth_admin",
        "user_authenticated": True,
        "user_email": admin.get("email"),
        "user_info": admin
    })


@router.get("/admin/google/oauth/status")
async def get_google_oauth_status(
    request: Request,
    admin: dict = Depends(require_admin_auth)
):
    """Get current Google OAuth configuration status"""
    try:
        ttw_manager = TTWOAuthManager()
        config = await ttw_manager.get_google_oauth_app_config()
        
        if config:
            # Also get credentials to include client_secret
            credentials = await ttw_manager.get_google_oauth_credentials()
            client_secret = credentials.get("client_secret", "") if credentials else ""
            
            # Check if we have active OAuth tokens (user connected)
            from database import get_google_oauth_tokens, get_portfolio_id
            tokens = await get_google_oauth_tokens(
                portfolio_id=get_portfolio_id()
            )
            
            connected = bool(tokens and tokens.get('access_token'))
            account_email = tokens.get('admin_email') if tokens else None
            
            return JSONResponse({
                "configured": True,
                "connected": connected,
                "account_email": account_email,
                "client_id": config.get("client_id", ""),
                "client_secret": client_secret,
                "redirect_uri": config.get("redirect_uri", "")
            })
        else:
            return JSONResponse({
                "configured": False,
                "client_id": "",
                "client_secret": "",
                "redirect_uri": ""
            })
    except Exception as e:
        log_with_context(
            "ERROR", "get_google_oauth_status",
            f"Failed to get Google OAuth status: {e}",
            request
        )
        return JSONResponse({
            "configured": False,
            "client_id": "",
            "client_secret": "",
            "redirect_uri": "",
            "error": str(e)
        })


@router.get("/admin/google/oauth/select-scopes")
async def show_scope_selection(
    request: Request,
    admin: dict = Depends(require_admin_auth)
):
    """Show scope selection page for OAuth authorization"""
    return templates.TemplateResponse("google_oauth_scope_selection.html", {
        "request": request,
        "current_page": "google_oauth_admin",
        "user_info": admin
    })


@router.post("/admin/google/oauth/authorize-with-scopes")
async def initiate_oauth_with_selected_scopes(
    request: Request,
    scope_data: dict,
    admin: dict = Depends(require_admin_auth)
):
    """Initiate Google OAuth authorization with user-selected scopes"""
    try:
        selected_scopes = scope_data.get('scopes', [])
        
        # Validate required scopes
        required_scopes = ['openid', 'email', 'profile']
        if not all(scope in selected_scopes for scope in required_scopes):
            return JSONResponse(
                {"detail": "Required scopes (openid, email, profile) must be selected"},
                status_code=400
            )
        
        # Generate state token and store in session
        state = secrets.token_urlsafe(32)
        request.session['oauth_state'] = state
        
        ttw_manager = TTWOAuthManager()
        
        # Get the authorization URL with selected scopes
        auth_url = await ttw_manager.get_google_auth_url(
            scopes=selected_scopes,
            state=state
        )
        
        if not auth_url:
            return JSONResponse(
                {"detail": "Google OAuth is not configured."},
                status_code=503
            )

        # Create OAuth session record
        from database import create_oauth_session, get_portfolio_id
        
        google_config = await ttw_manager.get_google_oauth_credentials()
        scope_string = ' '.join(selected_scopes)
        
        await create_oauth_session(
            portfolio_id=get_portfolio_id(),
            state=state,
            scopes=scope_string,
            auth_url=auth_url,
            redirect_uri=google_config['redirect_uri'],
            admin_email=admin.get('email')
        )

        log_with_context(
            "INFO", "oauth_authorization_with_scopes",
            f"OAuth session created with selected scopes: {selected_scopes} "
            f"for user: {admin.get('email')}",
            request
        )
        
        return JSONResponse({
            "auth_url": auth_url,
            "selected_scopes": selected_scopes
        })
        
    except Exception as e:
        log_with_context(
            "ERROR", "initiate_oauth_with_selected_scopes",
            f"Failed to initiate OAuth with selected scopes: {e}",
            request
        )
        return JSONResponse(
            {"detail": f"Server error: {str(e)}"},
            status_code=500
        )


@router.get("/admin/google/oauth/authorize")
async def initiate_google_oauth_authorization(
    request: Request
):
    """Handle OAuth authorization - redirect to scope selection or return JSON for AJAX"""
    try:
        # Check if this is an AJAX request
        accept_header = request.headers.get("Accept", "")
        content_type = request.headers.get("Content-Type", "")
        is_ajax = (
            request.headers.get("X-Requested-With") == "XMLHttpRequest" or
            "application/json" in accept_header or
            "application/json" in content_type or
            accept_header == "application/json"
        )
        
        # Check authentication manually to provide better error handling
        payload = None
        try:
            # Get token from cookie (admin users will have this)
            token = request.cookies.get("access_token")
            if not token:
                if is_ajax:
                    return JSONResponse(
                        {"detail": "Authentication required. Please log in again."},
                        status_code=401
                    )
                return RedirectResponse(
                    url="/admin/google/oauth?error=auth_required",
                    status_code=302
                )
            
            # Verify the token manually
            from auth import verify_token, is_authorized_user
            try:
                payload = verify_token(token)
                email = payload.get("sub")
                if not email or not is_authorized_user(email):
                    if is_ajax:
                        return JSONResponse(
                            {"detail": "Authentication required. Please log in again."},
                            status_code=401
                        )
                    return RedirectResponse(
                        url="/admin/google/oauth?error=auth_required",
                        status_code=302
                    )
            except Exception:
                if is_ajax:
                    return JSONResponse(
                        {"detail": "Authentication required. Please log in again."},
                        status_code=401
                    )
                return RedirectResponse(
                    url="/admin/google/oauth?error=auth_required",
                    status_code=302
                )
        except Exception:
            if is_ajax:
                return JSONResponse(
                    {"detail": "Authentication required. Please log in again."},
                    status_code=401
                )
            return RedirectResponse(
                url="/admin/google/oauth?error=auth_required",
                status_code=302
            )
        
        if is_ajax:
            # For AJAX requests, generate OAuth URL and return it directly
            # Generate state token and store in session
            state = secrets.token_urlsafe(32)
            request.session['oauth_state'] = state
            
            ttw_manager = TTWOAuthManager()
            
            # Get the authorization URL for admin scopes (including Gmail send)
            # Force consent screen to show additional permissions
            auth_url = await ttw_manager.get_google_auth_url(
                scopes=[
                    'openid',
                    'email',
                    'profile',
                    'https://www.googleapis.com/auth/gmail.send',
                    'https://www.googleapis.com/auth/gmail.readonly'
                ],
                state=state,
                force_consent=True  # This will force the consent screen
            )
            
            if not auth_url:
                return JSONResponse(
                    {"detail": "Google OAuth is not configured."},
                    status_code=503
                )

            # Create OAuth session record
            from database import create_oauth_session, get_portfolio_id
            
            google_config = await ttw_manager.get_google_oauth_credentials()
            scope_string = ('openid email profile '
                            'https://www.googleapis.com/auth/gmail.send '
                            'https://www.googleapis.com/auth/gmail.readonly')
            
            await create_oauth_session(
                portfolio_id=get_portfolio_id(),
                state=state,
                scopes=scope_string,
                auth_url=auth_url,
                redirect_uri=google_config['redirect_uri'],
                admin_email=payload.get('email')
            )

            log_with_context(
                "INFO", "admin_oauth_authorization_ajax",
                f"Admin OAuth session created with state: {state} "
                f"for user: {payload.get('email')}",
                request
            )
            
            return JSONResponse({
                "auth_url": auth_url
            })
        else:
            # For direct browser requests, redirect to scope selection page
            return RedirectResponse(
                url="/admin/google/oauth/select-scopes",
                status_code=302
            )
        
    except Exception as e:
        log_with_context(
            "ERROR", "initiate_google_oauth_authorization",
            f"Failed to handle OAuth authorization: {e}",
            request
        )
        if is_ajax:
            return JSONResponse(
                {"detail": f"Server error: {str(e)}"},
                status_code=500
            )
        return RedirectResponse(
            url="/admin/google/oauth?error=server_error",
            status_code=302
        )


@router.get("/admin/google/oauth/authorize-direct")
async def initiate_google_oauth_authorization_direct(
    request: Request
):
    """Initiate Google OAuth authorization flow for admin permissions"""
    try:
        # Check authentication manually to provide better error handling
        try:
            # Get token from cookie (admin users will have this)
            token = request.cookies.get("access_token")
            if not token:
                return JSONResponse(
                    {"detail": "Authentication required. Please log in again."},
                    status_code=401
                )
            
            # Verify the token manually
            from auth import verify_token, is_authorized_user
            try:
                payload = verify_token(token)
                email = payload.get("sub")
                if not email or not is_authorized_user(email):
                    return JSONResponse(
                        {"detail": "Authentication required. "
                         "Please log in again."},
                        status_code=401
                    )
                user = payload
            except Exception:
                return JSONResponse(
                    {"detail": "Authentication required. Please log in again."},
                    status_code=401
                )
        except Exception:
            return JSONResponse(
                {"detail": "Authentication required. Please log in again."},
                status_code=401
            )
        
        # Generate state token and store in session like regular login flow
        state = secrets.token_urlsafe(32)
        request.session['oauth_state'] = state
        
        ttw_manager = TTWOAuthManager()
        
        # Get the authorization URL for admin scopes (including Gmail send)
        auth_url = await ttw_manager.get_google_auth_url(
            scopes=[
                'openid',
                'email',
                'profile',
                'https://www.googleapis.com/auth/gmail.send',
                'https://www.googleapis.com/auth/gmail.readonly'
            ],
            state=state,  # Pass the state we generated
            force_consent=True  # Force consent for admin authorization
        )
        
        if not auth_url:
            return JSONResponse(
                {"detail": "Google OAuth is not configured."},
                status_code=503
            )

        # Create OAuth session record like the regular login flow
        from database import create_oauth_session, get_portfolio_id
        
        google_config = await ttw_manager.get_google_oauth_credentials()
        scope_string = ('openid email profile '
                        'https://www.googleapis.com/auth/gmail.send '
                        'https://www.googleapis.com/auth/gmail.readonly')
        
        await create_oauth_session(
            portfolio_id=get_portfolio_id(),
            state=state,
            scopes=scope_string,
            auth_url=auth_url,
            redirect_uri=google_config['redirect_uri'],
            admin_email=user.get('email')
        )

        log_with_context(
            "INFO", "admin_oauth_authorization",
            f"Admin OAuth session created with state: {state} "
            f"for user: {user.get('email')}",
            request
        )
        
        return JSONResponse({
            "auth_url": auth_url
        })
        
    except Exception as e:
        log_with_context(
            "ERROR", "initiate_google_oauth_authorization",
            f"Failed to initiate Google OAuth authorization: {e}",
            request
        )
        return JSONResponse(
            {"detail": f"Server error: {str(e)}"},
            status_code=500
        )


@router.get("/admin/google/oauth/scopes")
async def get_google_oauth_scopes(
    admin: dict = Depends(require_admin_auth)
):
    """Get current Google OAuth scopes status"""
    try:
        from database import get_google_oauth_tokens, get_portfolio_id
        
        # Get the most recent active OAuth tokens
        tokens = await get_google_oauth_tokens(
            portfolio_id=get_portfolio_id()
        )
        
        if not tokens:
            return JSONResponse({
                "status": "error",
                "message": "No active OAuth tokens found",
                "scopes": {
                    "openid": False,
                    "email": False,
                    "profile": False,
                    "https://www.googleapis.com/auth/gmail.send": False
                }
            })
        
        # Parse the granted scopes string
        granted_scopes_str = tokens.get('granted_scopes', '')
        granted_scopes = (granted_scopes_str.split()
                          if granted_scopes_str else [])
        
        # Check each required scope
        scope_status = {
            "openid": "openid" in granted_scopes,
            "email": "email" in granted_scopes,
            "profile": "profile" in granted_scopes,
            "https://www.googleapis.com/auth/gmail.send":
                "https://www.googleapis.com/auth/gmail.send" in granted_scopes
        }
        
        return JSONResponse({
            "status": "success",
            "scopes": scope_status,
            "granted_scopes": granted_scopes,
            "last_updated": tokens.get('completed_at'),
            "token_expires_at": tokens.get('token_expires_at')
        })
        
    except Exception as e:
        log_with_context(
            "ERROR", "get_google_oauth_scopes",
            f"Failed to get Google OAuth scopes: {e}"
        )
        return JSONResponse({
            "status": "error",
            "message": f"Server error: {str(e)}",
            "scopes": {
                "openid": False,
                "email": False,
                "profile": False,
                "https://www.googleapis.com/auth/gmail.send": False
            }
        }, status_code=500)


@router.post("/admin/google/oauth/revoke-scope")
async def revoke_google_oauth_scope(
    request: Request,
    admin: dict = Depends(require_admin_auth)
):
    """Revoke a specific Google OAuth scope"""
    try:
        data = await request.json()
        scope_to_revoke = data.get('scope')
        
        if not scope_to_revoke:
            return JSONResponse({
                "status": "error",
                "message": "Scope parameter is required"
            }, status_code=400)
        
        from database import get_google_oauth_tokens, get_portfolio_id
        
        # Get current tokens
        tokens = await get_google_oauth_tokens(
            portfolio_id=get_portfolio_id()
        )
        
        if not tokens:
            return JSONResponse({
                "status": "error",
                "message": "No active OAuth tokens found"
            }, status_code=404)
        
        access_token = tokens.get('access_token')
        if not access_token:
            return JSONResponse({
                "status": "error",
                "message": "No access token available"
            }, status_code=404)
        
        # Revoke the specific scope with Google
        revoke_url = "https://oauth2.googleapis.com/revoke"
        revoke_data = {"token": access_token}
        
        async with httpx.AsyncClient() as client:
            response = await client.post(revoke_url, data=revoke_data)
            
        if response.status_code == 200:
            # Update database to mark tokens as revoked
            from database import revoke_oauth_tokens
            await revoke_oauth_tokens(
                portfolio_id=get_portfolio_id(),
                reason=f"Scope {scope_to_revoke} revoked by admin"
            )
            
            log_with_context(
                "INFO", "revoke_google_oauth_scope",
                f"Successfully revoked Google OAuth scope: {scope_to_revoke}",
                request
            )
            
            return JSONResponse({
                "status": "success",
                "message": f"Successfully revoked {scope_to_revoke}",
                "revoked_scope": scope_to_revoke
            })
        else:
            return JSONResponse({
                "status": "error",
                "message": (f"Failed to revoke scope with Google: "
                            f"{response.text}")
            }, status_code=response.status_code)
            
    except Exception as e:
        log_with_context(
            "ERROR", "revoke_google_oauth_scope",
            f"Failed to revoke Google OAuth scope: {e}",
            request
        )
        return JSONResponse({
            "status": "error",
            "message": f"Server error: {str(e)}"
        }, status_code=500)


@router.post("/admin/google/oauth/config")
async def save_google_oauth_config(
    request: Request,
    admin: dict = Depends(require_admin_auth)
):
    config = await request.json()
    ttw_manager = TTWOAuthManager()
    success = await ttw_manager.configure_google_oauth_app(config)
    if success:
        return JSONResponse(
            {"status": "success",
             "message": "Google OAuth configuration saved."}
        )
    raise HTTPException(
        status_code=500,
        detail="Failed to save Google OAuth configuration."
    )

# --- LinkedIn OAuth Admin Endpoints ---


@router.get("/admin/linkedin/oauth", response_class=HTMLResponse)
async def linkedin_oauth_admin_page(
    request: Request,
    admin: dict = Depends(require_admin_auth)
):
    return templates.TemplateResponse("linkedin_oauth_admin.html", {
        "request": request,
        "current_page": "linkedin_oauth_admin",
        "user_info": admin
    })


@router.post("/admin/linkedin/oauth/config")
async def save_linkedin_oauth_config(
    request: Request,
    admin: dict = Depends(require_admin_auth)
):
    config = await request.json()
    ttw_manager = TTWOAuthManager()
    success = await ttw_manager.configure_linkedin_oauth_app(config)
    if success:
        return JSONResponse(
            {"status": "success",
             "message": "LinkedIn OAuth configuration saved."}
        )
    raise HTTPException(
        status_code=500,
        detail="Failed to save LinkedIn OAuth configuration."
    )


@router.get("/admin/linkedin/oauth/callback")
async def linkedin_oauth_callback(request: Request, code: str, state: str):
    ttw_manager = TTWOAuthManager()
    try:
        state_data = ttw_manager.verify_linkedin_state(state)
        await ttw_manager.exchange_linkedin_code_for_tokens(code, state_data)
        return templates.TemplateResponse(
            "linkedin_oauth_success.html", {"request": request}
        )
    except Exception as e:
        log_with_context(
            "ERROR", "linkedin_oauth_callback",
            f"LinkedIn OAuth callback error: {e}", request, exc_info=True
        )
        return templates.TemplateResponse(
            "linkedin_oauth_error.html", {"request": request, "error": str(e)}
        )


@router.post("/admin/linkedin/sync")
async def sync_linkedin_profile_data(
    admin: dict = Depends(require_admin_auth)
):
    from ttw_linkedin_sync import TTWLinkedInSync
    sync_service = TTWLinkedInSync()
    result = await sync_service.sync_profile_data()
    if result.get("success"):
        return JSONResponse(result)
    raise HTTPException(
        status_code=500, detail=result.get("error", "Sync failed.")
    )


# --- Admin Fallback Login Routes ---

@router.get("/auth/admin-login")
async def show_admin_login(request: Request, error: str = None):
    """Show admin login form as fallback when OAuth fails"""
    return templates.TemplateResponse(
        "admin_login.html", 
        {"request": request, "error": error}
    )


@router.post("/auth/admin-login")
async def admin_login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...)
):
    """Handle admin login form submission"""
    import secrets
    
    # Verify credentials using constant-time comparison
    correct_username = secrets.compare_digest(username, ADMIN_USERNAME)
    correct_password = secrets.compare_digest(password, ADMIN_PASSWORD)
    
    if not (correct_username and correct_password):
        log_with_context(
            "WARNING", "admin_login",
            f"Failed admin login attempt for username: {username}", request
        )
        return templates.TemplateResponse(
            "admin_login.html",
            {"request": request, "error": "Invalid username or password"}
        )
    
    # Use the first authorized email for admin login token
    if not AUTHORIZED_EMAILS:
        log_with_context(
            "ERROR", "admin_login",
            "No authorized emails configured for admin login", request
        )
        return templates.TemplateResponse(
            "admin_login.html",
            {"request": request, "error": "Admin access not configured"}
        )
    
    admin_email = AUTHORIZED_EMAILS[0]  # Use first authorized email
    
    log_with_context(
        "INFO", "admin_login",
        f"Successful admin login for {admin_email}", request
    )
    
    # Create access token for admin user
    access_token = create_access_token(
        data={"sub": admin_email, "name": "Administrator", "iss": "admin"}
    )
    
    # Create a simple success page with token for the popup
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Login Successful</title>
        <style>
            body {{ 
                font-family: Arial, sans-serif; 
                text-align: center; 
                padding: 50px;
                background: #f8f9fa;
            }}
            .success {{ 
                background: #d4edda; 
                color: #155724; 
                padding: 20px; 
                border-radius: 8px;
                margin: 20px auto;
                max-width: 400px;
                border: 1px solid #c3e6cb;
            }}
        </style>
    </head>
    <body>
        <div class="success">
            <h2>Login Successful!</h2>
            <p>Redirecting to admin dashboard...</p>
        </div>
        <script>
            // Store token in localStorage and redirect
            localStorage.setItem('access_token', '{access_token}');
            
            // If this is in a popup, close it and refresh parent
            if (window.opener) {{
                window.opener.location.href = '/admin/google-oauth/';
                window.close();
            }} else {{
                // If not in popup, redirect directly
                window.location.href = '/admin/google-oauth/';
            }}
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)


@router.get("/admin/google/oauth/tokens")
async def view_oauth_tokens_graphql(
    request: Request,
    admin: dict = Depends(require_admin_auth)
):
    """View OAuth tokens in GraphQL format"""
    try:
        from database import get_google_oauth_tokens, get_portfolio_id
        
        # Get OAuth token for this portfolio (returns single token, not list)
        token = await get_google_oauth_tokens(
            portfolio_id=get_portfolio_id()
        )
        
        if not token:
            graphql_response = {
                "data": {
                    "oauthToken": None
                },
                "extensions": {
                    "message": "No OAuth token found"
                }
            }
            return JSONResponse(graphql_response)
        
        # Format token in GraphQL-style response
        token_entry = {
            "id": token.get('id'),
            "provider": token.get('provider', 'google'),
            "createdAt": token.get('created_at'),
            "updatedAt": token.get('updated_at'),
            "adminEmail": token.get('admin_email'),
            "scopes": {
                "granted": token.get('granted_scopes', '').split(' ') if token.get('granted_scopes') else [],
                "count": len(token.get('granted_scopes', '').split(' ')) if token.get('granted_scopes') else 0
            },
            "tokenInfo": {
                "hasAccessToken": bool(token.get('access_token')),
                "hasRefreshToken": bool(token.get('refresh_token')),
                "expiresAt": token.get('token_expires_at'),
                "tokenType": token.get('token_type', 'Bearer')
            },
            "status": {
                "isActive": bool(token.get('access_token')),
                "isExpired": False  # We'd need to check expiry logic here
            }
        }
        
        graphql_response = {
            "data": {
                "oauthToken": token_entry
            },
            "extensions": {
                "query": "query GetOAuthToken { oauthToken { id provider createdAt scopes { granted count } tokenInfo { hasAccessToken hasRefreshToken } status { isActive } } }",
                "executionTime": "0ms",
                "source": "Blackburn Systems OAuth API"
            }
        }
        
        log_with_context(
            "INFO", "view_oauth_tokens",
            f"Returned OAuth token for admin: {admin.get('email')}",
            request
        )
        
        return JSONResponse(graphql_response)
        
    except Exception as e:
        log_with_context(
            "ERROR", "view_oauth_tokens",
            f"Failed to retrieve OAuth tokens: {e}",
            request
        )
        
        error_response = {
            "data": None,
            "errors": [
                {
                    "message": f"Failed to retrieve OAuth tokens: {str(e)}",
                    "extensions": {
                        "code": "INTERNAL_ERROR",
                        "timestamp": "2024-09-11T14:39:00Z"
                    }
                }
            ]
        }
        
        return JSONResponse(error_response, status_code=500)
