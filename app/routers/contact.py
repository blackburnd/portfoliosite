from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import uuid
import traceback
import os
import base64
import logging

from auth import verify_token, is_authorized_user
from database import (
    database, get_google_oauth_tokens, save_google_oauth_tokens,
    update_google_oauth_token_usage, get_portfolio_id
)
from log_capture import add_log
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GoogleRequest
from googleapiclient.discovery import build
from ttw_oauth_manager import TTWOAuthManager


router = APIRouter()
templates = Jinja2Templates(directory="templates")
logger = logging.getLogger('portfoliosite')


async def send_contact_email(
    name: str, email: str, subject: str, message: str, contact_id: int
):
    """Send email notification using Gmail API."""
    try:
        recipient_email = os.getenv(
            "CONTACT_NOTIFICATION_EMAIL", "blackburnd@gmail.com"
        )

        portfolio_id = get_portfolio_id()
        oauth_data = await get_google_oauth_tokens(portfolio_id)

        if not oauth_data or not oauth_data.get('access_token'):
            logger.warning(
                "Gmail API: No OAuth credentials found for email sending"
            )
            add_log(
                "WARNING", "Gmail API: No OAuth credentials found",
                "gmail_api_no_credentials"
            )
            return False

        # Debug logging for oauth_data structure
        logger.info(f"Gmail API: OAuth data keys: {list(oauth_data.keys())}")
        logger.info(
            f"Gmail API: Token expires at: "
            f"{oauth_data.get('token_expires_at')}"
        )

        ttw_manager = TTWOAuthManager()
        google_config = await ttw_manager.get_oauth_app_config(
            provider='google'
        )

        if not google_config:
            logger.warning("Gmail API: No OAuth app configuration found")
            add_log(
                "WARNING", "Gmail API: No OAuth app configuration found",
                "gmail_api_no_config"
            )
            return False

        # Parse expiry time if available
        expiry = None
        if oauth_data.get('token_expires_at'):
            from datetime import datetime
            expiry = datetime.fromisoformat(oauth_data['token_expires_at'])

        credentials = Credentials(
            token=oauth_data['access_token'],
            refresh_token=oauth_data.get('refresh_token'),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=google_config['client_id'],
            client_secret=google_config['client_secret'],
            scopes=oauth_data['granted_scopes'].split(),
            expiry=expiry
        )

        # Check if credentials are expired and refresh if needed
        try:
            # Check if we have a refresh token before checking expiry
            if credentials.refresh_token:
                # Safely check if credentials are expired
                try:
                    is_expired = credentials.expired
                except Exception as expiry_error:
                    logger.warning(
                        f"Gmail API: Could not check credential expiry: "
                        f"{expiry_error}"
                    )
                    # Assume expired if we can't check
                    is_expired = True
                
                if is_expired:
                    logger.info("Gmail API: Refreshing expired credentials")
                    credentials.refresh(GoogleRequest())
                    await save_google_oauth_tokens(
                        portfolio_id,
                        oauth_data['admin_email'],
                        credentials.token,
                        credentials.refresh_token,
                        credentials.expiry,
                        " ".join(credentials.scopes)
                    )
            else:
                logger.warning("Gmail API: No refresh token available")
        except Exception as refresh_error:
            logger.error(
                f"Gmail API: Error during credential refresh: {refresh_error}"
            )
            # Continue with existing credentials

        service = build('gmail', 'v1', credentials=credentials)

        email_body = f"""
New contact form submission received:

Contact ID: {contact_id}
Name: {name}
Email: {email}
Subject: {subject or 'No Subject'}

Message:
{message}

---
This email was automatically generated from your portfolio website.
        """.strip()

        message_obj = {
            'raw': base64.urlsafe_b64encode(
                f"To: {recipient_email}\r\n"
                f"From: {recipient_email}\r\n"
                f"Subject: New Contact Form Submission #{contact_id}: "
                f"{subject or 'No Subject'}\r\n"
                f"Content-Type: text/plain; charset=utf-8\r\n\r\n"
                f"{email_body}".encode('utf-8')
            ).decode('utf-8')
        }

        result = service.users().messages().send(
            userId='me', body=message_obj
        ).execute()

        await update_google_oauth_token_usage(
            portfolio_id, oauth_data['admin_email']
        )

        logger.info(
            f"Gmail API: Contact notification email sent for submission "
            f"#{contact_id}, Message ID: {result.get('id')}"
        )
        add_log(
            "INFO",
            f"Gmail API: Email sent for submission #{contact_id}, "
            f"Message ID: {result.get('id')}",
            "gmail_api_email_sent"
        )
        return True

    except Exception as e:
        full_traceback = traceback.format_exc()
        logger.error(f"Gmail API: Failed to send email: {str(e)}")
        logger.error(f"Gmail API error traceback: {full_traceback}")
        add_log(
            "ERROR", f"Gmail API: Failed to send email: {str(e)}",
            "gmail_api_email_error"
        )
        add_log(
            "ERROR", f"Gmail API traceback: {full_traceback}",
            "gmail_api_traceback"
        )
        return False


@router.get("/contact/", response_class=HTMLResponse)
async def contact(request: Request):
    """Serve the contact page"""
    user_authenticated = False
    user_email = None

    try:
        token = request.cookies.get("access_token")
        if token:
            payload = verify_token(token)
            email = payload.get("sub")
            if email and is_authorized_user(email):
                user_authenticated = True
                user_email = email
    except Exception:
        pass

    return templates.TemplateResponse("contact.html", {
        "request": request,
        "current_page": "contact",
        "user_authenticated": user_authenticated,
        "user_email": user_email,
        "user_info": {"email": user_email} if user_authenticated else None
    })


@router.post("/contact/submit")
async def contact_submit(request: Request):
    """Handle contact form submission"""
    try:
        form = await request.form()

        name = form.get("name", "").strip()
        email = form.get("email", "").strip()
        subject = form.get("subject", "").strip()
        message = form.get("message", "").strip()

        if not name or not email or not message:
            missing = [
                f for f in ['name', 'email', 'message'] if not locals().get(f)
            ]
            add_log(
                level="WARNING",
                module="contact_form",
                message="Contact form validation failed",
                function="contact_submit",
                extra={"missing_fields": missing, "ip": request.client.host}
            )
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "message": "Name, email, and message are required."
                }
            )

        portfolio_query = "SELECT portfolio_id FROM portfolios LIMIT 1"
        portfolio_result = await database.fetch_one(portfolio_query)

        if not portfolio_result:
            raise Exception("No portfolio found in database")

        portfolio_id = portfolio_result['portfolio_id']

        query = """
            INSERT INTO contact_messages
            (portfolio_id, name, email, subject, message, created_at,
             is_read)
            VALUES (:portfolio_id, :name, :email, :subject, :message, NOW(),
                    FALSE)
            RETURNING id
        """
        result = await database.fetch_one(
            query,
            {
                "portfolio_id": portfolio_id,
                "name": name,
                "email": email,
                "subject": subject,
                "message": message
            }
        )

        contact_id = result['id'] if result else None

        logger.info(
            f"Contact form submitted: ID {contact_id}, from {name} ({email})"
        )

        email_sent = await send_contact_email(
            name, email, subject, message, contact_id
        )

        add_log(
            level="INFO",
            module="contact_form",
            message=f"Contact form submitted successfully: ID {contact_id}",
            function="contact_submit",
            extra=f"Email sent: {email_sent}"
        )

        return RedirectResponse(url="/contact/thank-you", status_code=303)

    except Exception as e:
        error_id = str(uuid.uuid4())[:8]
        error_traceback = traceback.format_exc()
        logger.error(
            f"CONTACT FORM ERROR [{error_id}]: {str(e)}\n{error_traceback}"
        )
        add_log(
            level="ERROR",
            module="contact_form",
            message=f"[{error_id}] Contact form submission failed: {str(e)}",
            function="contact_submit",
            extra={"error_id": error_id, "traceback": error_traceback}
        )
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": "An error occurred."}
        )


@router.get("/contact/thank-you", response_class=HTMLResponse)
async def contact_thank_you(request: Request):
    """Display thank you page after contact form submission"""
    user_authenticated = False
    user_email = None

    try:
        token = request.cookies.get("access_token")
        if token:
            payload = verify_token(token)
            email = payload.get("sub")
            if email and is_authorized_user(email):
                user_authenticated = True
                user_email = email
    except Exception:
        pass

    return templates.TemplateResponse("contact_thank_you.html", {
        "request": request,
        "title": "Thank You - Daniel Blackburn",
        "user_authenticated": user_authenticated,
        "user_email": user_email,
        "user_info": {"email": user_email} if user_authenticated else None
    })
