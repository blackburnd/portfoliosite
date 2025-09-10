import os
import secrets
import httpx
from urllib.parse import urlencode

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from jose import jwt, jwk
from jose.exceptions import JWTError

from auth import (
    is_authorized_user,
    create_access_token,
    require_admin_auth,
    SECRET_KEY,
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from log_capture import log_with_context
from ttw_oauth_manager import TTWOAuthManager

router = APIRouter()
templates = Jinja2Templates(directory="templates")


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

        scope = 'openid email profile https://www.googleapis.com/auth/gmail.send'

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
        if error:
            log_with_context(
                "WARNING", "auth_callback", f"OAuth error received: {error}",
                request
            )
            return HTMLResponse(
                f"<h1>Authorization Error</h1><p>{error}</p>",
                status_code=400
            )

        callback_state = request.query_params.get('state')
        session_state = request.session.get('oauth_state')

        if not callback_state or callback_state != session_state:
            log_with_context(
                "ERROR", "auth_callback", "CSRF validation failed", request
            )
            return HTMLResponse(
                "<h1>Security Error</h1><p>CSRF validation failed.</p>",
                status_code=400
            )

        request.session.pop('oauth_state', None)

        code = request.query_params.get('code')
        if not code:
            return HTMLResponse(
                "<h1>Authentication Error</h1>"
                "<p>Authorization code not found.</p>",
                status_code=400
            )

        ttw_manager = TTWOAuthManager()
        google_config = await ttw_manager.get_google_oauth_app_config()
        if not google_config:
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
            raise HTTPException(
                status_code=500,
                detail="Could not retrieve Google's public keys."
            )

        try:
            header = jwt.get_unverified_header(id_token)
            kid = header['kid']

            key = next((k for k in keys if k['kid'] == kid), None)
            if not key:
                raise JWTError("Public key not found for token.")

            public_key = jwk.construct(key)

            user_info = jwt.decode(
                id_token,
                public_key,
                algorithms=[header['alg']],
                audience=google_config['client_id'],
                issuer='https://accounts.google.com'
            )
            email = user_info.get('email')

        except JWTError as e:
            log_with_context(
                "ERROR", "auth_callback",
                f"ID Token verification failed: {e}", request
            )
            return HTMLResponse(
                "<h1>Security Error</h1><p>Invalid token signature.</p>",
                status_code=400
            )

        if not email or not is_authorized_user(email):
            log_with_context(
                "WARNING", "auth",
                f"Unauthorized login attempt by {email}", request
            )
            return HTMLResponse(
                f"<h1>Access Denied</h1><p>Email {email} is not authorized.</p>",
                status_code=403
            )

        access_token = create_access_token(data={"sub": email})
        log_with_context(
            "INFO", "auth", f"Successful login by {email} - JWT created",
            request
        )

        response = HTMLResponse("""
            <html><head><title>Authentication Successful</title><script>
                if (window.opener) {
                    window.opener.postMessage(
                        { type: 'OAUTH_SUCCESS' }, window.location.origin
                    );
                    window.close();
                } else { window.location.href = '/workadmin'; }
            </script></head><body><p>Auth successful. Closing...</p></body>
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
        "user_info": admin
    })


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
