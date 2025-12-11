from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import uuid
import traceback
import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from auth import verify_token, is_authorized_user
from database import database, get_portfolio_id
from log_capture import add_log


router = APIRouter()
templates = Jinja2Templates(directory="templates")
logger = logging.getLogger('portfoliosite')


async def send_contact_email(
    name: str, email: str, subject: str, message: str, contact_id: int
):
    """Send email notification using SMTP."""
    try:
        # Get SMTP configuration from environment variables
        smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_username = os.getenv("SMTP_USERNAME")
        smtp_password = os.getenv("SMTP_PASSWORD")
        smtp_from_email = os.getenv("SMTP_FROM_EMAIL", smtp_username)
        recipient_email = os.getenv(
            "CONTACT_NOTIFICATION_EMAIL", "blackburnd@gmail.com"
        )

        # Check if SMTP is configured
        if not smtp_username or not smtp_password:
            logger.warning(
                "SMTP not configured. Set SMTP_USERNAME and SMTP_PASSWORD "
                "environment variables."
            )
            add_log(
                "WARNING", 
                "SMTP not configured - email notification skipped",
                "smtp_not_configured"
            )
            return False

        # Create email message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"New Contact Form Submission #{contact_id}: {subject or 'No Subject'}"
        msg['From'] = smtp_from_email
        msg['To'] = recipient_email
        msg['Reply-To'] = email

        # Email body
        text_body = f"""
New contact form submission received:

Contact ID: {contact_id}
Name: {name}
Email: {email}
Subject: {subject or 'No Subject'}

Message:
{message}

---
This email was automatically generated from your portfolio website.
Reply directly to this email to respond to {name}.
        """.strip()

        html_body = f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <h2 style="color: #667eea;">New Contact Form Submission</h2>
    <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
        <p><strong>Contact ID:</strong> {contact_id}</p>
        <p><strong>Name:</strong> {name}</p>
        <p><strong>Email:</strong> <a href="mailto:{email}">{email}</a></p>
        <p><strong>Subject:</strong> {subject or 'No Subject'}</p>
    </div>
    <div style="background: white; padding: 20px; border-left: 4px solid #667eea; margin: 20px 0;">
        <h3>Message:</h3>
        <p style="white-space: pre-wrap;">{message}</p>
    </div>
    <hr style="border: none; border-top: 1px solid #e1e5e9; margin: 30px 0;">
    <p style="font-size: 12px; color: #666;">
        This email was automatically generated from your portfolio website.<br>
        Reply directly to this email to respond to {name}.
    </p>
</body>
</html>
        """.strip()

        # Attach both plain text and HTML versions
        part1 = MIMEText(text_body, 'plain')
        part2 = MIMEText(html_body, 'html')
        msg.attach(part1)
        msg.attach(part2)

        # Send email via SMTP
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(msg)

        logger.info(
            f"SMTP: Contact notification email sent for submission #{contact_id}"
        )
        add_log(
            "INFO",
            f"Email notification sent for contact submission #{contact_id}",
            "contact_email_sent"
        )
        return True

    except Exception as e:
        full_traceback = traceback.format_exc()
        logger.error(f"SMTP: Failed to send email: {str(e)}")
        logger.error(f"SMTP error traceback: {full_traceback}")
        add_log(
            "ERROR", 
            f"Failed to send contact email: {str(e)}",
            "contact_email_error",
            extra={"traceback": full_traceback}
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

        if not email_sent:
            logger.warning(
                f"Contact #{contact_id}: Email notification failed to send. "
                "Check Gmail OAuth configuration at /admin/google/oauth"
            )
            add_log(
                level="WARNING",
                module="contact_form",
                message=f"Contact #{contact_id}: Email failed - OAuth may not be configured",
                function="contact_submit",
                extra="Visit /admin/google/oauth to authorize Gmail API"
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
