"""
SMTP Configuration Admin Router
TTW interface for managing SMTP email settings
"""
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import logging
import os

from auth import require_admin_auth
from database import database, get_portfolio_id

router = APIRouter()
templates = Jinja2Templates(directory="templates")
logger = logging.getLogger('portfoliosite')


@router.get("/admin/smtp", response_class=HTMLResponse)
async def smtp_admin_page(
    request: Request,
    admin: dict = Depends(require_admin_auth)
):
    """Display SMTP configuration admin page"""
    return templates.TemplateResponse("smtp_admin.html", {
        "request": request,
        "current_page": "smtp_admin",
        "user_authenticated": True,
        "user_email": admin.get("email", ""),
        "user_info": admin
    })


@router.get("/admin/smtp/status")
async def get_smtp_status(
    request: Request,
    admin: dict = Depends(require_admin_auth)
):
    """Get current SMTP configuration status"""
    try:
        portfolio_id = get_portfolio_id()
        
        # Check database for SMTP config
        query = """
        SELECT config_key, config_value 
        FROM site_config 
        WHERE portfolio_id = :portfolio_id 
        AND config_key LIKE 'smtp_%'
        ORDER BY config_key
        """
        
        rows = await database.fetch_all(query, {"portfolio_id": portfolio_id})
        
        config = {}
        for row in rows:
            # Return actual password so it can be edited
            config[row['config_key']] = row['config_value']
        
        # Check if all required settings are present
        required = ['smtp_username', 'smtp_password', 'smtp_host', 'smtp_port']
        is_configured = all(
            any(row['config_key'] == key for row in rows) 
            for key in required
        )
        
        return JSONResponse({
            "status": "success",
            "configured": is_configured,
            "config": config,
            "has_username": any(r['config_key'] == 'smtp_username' for r in rows),
            "has_password": any(r['config_key'] == 'smtp_password' for r in rows),
            "has_host": any(r['config_key'] == 'smtp_host' for r in rows)
        })
        
    except Exception as e:
        logger.error(f"Error getting SMTP status: {e}")
        return JSONResponse({
            "status": "error",
            "message": str(e)
        }, status_code=500)


@router.post("/admin/smtp/config")
async def save_smtp_config(
    request: Request,
    admin: dict = Depends(require_admin_auth)
):
    """Save SMTP configuration to database"""
    try:
        data = await request.json()
        portfolio_id = get_portfolio_id()
        
        # Settings to save
        settings = {
            'smtp_username': data.get('smtp_username', ''),
            'smtp_password': data.get('smtp_password', ''),
            'smtp_host': data.get('smtp_host', 'smtp.gmail.com'),
            'smtp_port': data.get('smtp_port', '587'),
            'smtp_from_email': data.get('smtp_from_email', ''),
            'contact_notification_email': data.get('contact_notification_email', '')
        }
        
        # Save each setting to site_config table
        for key, value in settings.items():
            # Skip password if it's the masked placeholder
            if key == 'smtp_password' and value == '********':
                continue
                
            query = """
            INSERT INTO site_config (portfolio_id, config_key, config_value, description)
            VALUES (:portfolio_id, :key, :value, :description)
            ON CONFLICT (portfolio_id, config_key)
            DO UPDATE SET 
                config_value = EXCLUDED.config_value,
                updated_at = NOW()
            """
            
            descriptions = {
                'smtp_username': 'SMTP username/email for sending contact notifications',
                'smtp_password': 'SMTP password (app password for Gmail)',
                'smtp_host': 'SMTP server hostname',
                'smtp_port': 'SMTP server port',
                'smtp_from_email': 'Email address to send from',
                'contact_notification_email': 'Email address to receive contact form notifications'
            }
            
            await database.execute(query, {
                "portfolio_id": portfolio_id,
                "key": key,
                "value": value,
                "description": descriptions.get(key, '')
            })
        
        logger.info(f"SMTP configuration updated by {admin.get('email')}")
        
        return JSONResponse({
            "status": "success",
            "message": "SMTP configuration saved successfully"
        })
        
    except Exception as e:
        logger.error(f"Error saving SMTP config: {e}")
        return JSONResponse({
            "status": "error",
            "message": str(e)
        }, status_code=500)


@router.post("/admin/smtp/test")
async def test_smtp_connection(
    request: Request,
    admin: dict = Depends(require_admin_auth)
):
    """Test SMTP connection and send a test email"""
    try:
        import smtplib
        from email.mime.text import MIMEText
        
        portfolio_id = get_portfolio_id()
        
        # Get SMTP config from database
        query = """
        SELECT config_key, config_value 
        FROM site_config 
        WHERE portfolio_id = :portfolio_id 
        AND config_key LIKE 'smtp_%'
        """
        
        rows = await database.fetch_all(query, {"portfolio_id": portfolio_id})
        config = {row['config_key']: row['config_value'] for row in rows}
        
        smtp_host = config.get('smtp_host', 'smtp.gmail.com')
        smtp_port = int(config.get('smtp_port', '587'))
        smtp_username = config.get('smtp_username')
        smtp_password = config.get('smtp_password')
        smtp_from = config.get('smtp_from_email', smtp_username)
        
        if not smtp_username or not smtp_password:
            return JSONResponse({
                "status": "error",
                "message": "SMTP username and password are required"
            }, status_code=400)
        
        # Get admin email
        admin_email = admin.get('email', admin.get('username', 'admin@blackburnsystems.com'))
        
        # Test connection
        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            
            # Send test email
            msg = MIMEText("This is a test email from your portfolio website SMTP configuration.")
            msg['Subject'] = "SMTP Test - Portfolio Website"
            msg['From'] = smtp_from
            msg['To'] = admin_email
            
            server.send_message(msg)
        
        logger.info(f"SMTP test successful, email sent to {admin_email}")
        
        return JSONResponse({
            "status": "success",
            "message": f"Test email sent successfully to {admin_email}"
        })
        
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"SMTP authentication failed: {e}")
        return JSONResponse({
            "status": "error",
            "message": "Authentication failed. Check your username and password."
        }, status_code=400)
    except smtplib.SMTPException as e:
        logger.error(f"SMTP error during test: {e}")
        return JSONResponse({
            "status": "error",
            "message": f"SMTP error: {str(e)}"
        }, status_code=400)
    except Exception as e:
        logger.error(f"Error testing SMTP: {e}", exc_info=True)
        return JSONResponse({
            "status": "error",
            "message": f"Error: {str(e)}"
        }, status_code=500)
