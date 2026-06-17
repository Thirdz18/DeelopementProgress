"""
Email Service - SMTP-based email sending for verification codes
"""
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from config import (
    EMAIL_ENABLED,
    EMAIL_HOST,
    EMAIL_PORT,
    EMAIL_USERNAME,
    EMAIL_PASSWORD,
    EMAIL_USE_TLS,
    EMAIL_FROM,
    EMAIL_FROM_NAME
)

logger = logging.getLogger(__name__)


def send_verification_email(
    to_email: str,
    code: str,
    purpose: str = "verification"
) -> bool:
    """
    Send verification code to user's email.
    
    Args:
        to_email: Recipient email address
        code: 6-digit verification code
        purpose: Purpose of verification (login, create, etc.)
        
    Returns:
        True if email sent successfully, False otherwise
    """
    if not EMAIL_ENABLED:
        logger.warning(f"Email not enabled - would send code {code} to {to_email}")
        logger.info(f"[DEV] Verification code for {to_email}: {code}")
        return False
    
    if not all([EMAIL_HOST, EMAIL_USERNAME, EMAIL_PASSWORD]):
        logger.error("Email configuration incomplete - missing host, username, or password")
        logger.info(f"[DEV] Verification code for {to_email}: {code}")
        return False
    
    try:
        # Build email
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f'Your GoodMarket Verification Code'
        msg['From'] = f'{EMAIL_FROM_NAME} <{EMAIL_FROM}>'
        msg['To'] = to_email
        
        # Plain text version
        text_content = f"""
Your GoodMarket Verification Code
================================

Your verification code is: {code}

This code will expire in 5 minutes.

If you didn't request this code, please ignore this email.

- The GoodMarket Team
        """.strip()
        
        # HTML version
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; background-color: #f4f4f4; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;">
    <div style="max-width: 480px; margin: 40px auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.1);">
        <div style="background: linear-gradient(135deg, #7c3aed 0%, #6d28d9 100%); padding: 32px; text-align: center;">
            <h1 style="color: #ffffff; margin: 0; font-size: 24px; font-weight: 700;">GoodMarket</h1>
            <p style="color: rgba(255,255,255,0.8); margin: 8px 0 0; font-size: 14px;">Verification Code</p>
        </div>
        <div style="padding: 32px; text-align: center;">
            <p style="color: #6b7280; font-size: 16px; margin: 0 0 24px;">Enter this code to verify your email:</p>
            <div style="background: #f3f4f6; border-radius: 8px; padding: 20px; display: inline-block;">
                <span style="font-family: 'Courier New', monospace; font-size: 32px; font-weight: 700; color: #7c3aed; letter-spacing: 8px;">{code}</span>
            </div>
            <p style="color: #9ca3af; font-size: 13px; margin: 24px 0 0;">This code expires in <strong>5 minutes</strong></p>
        </div>
        <div style="padding: 24px; background: #f9fafb; border-top: 1px solid #e5e7eb; text-align: center;">
            <p style="color: #9ca3af; font-size: 12px; margin: 0;">If you didn't request this code, you can safely ignore this email.</p>
        </div>
    </div>
</body>
</html>
        """.strip()
        
        # Attach both versions
        msg.attach(MIMEText(text_content, 'plain'))
        msg.attach(MIMEText(html_content, 'html'))
        
        # Send email
        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
            if EMAIL_USE_TLS:
                server.starttls()
            server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
            server.sendmail(EMAIL_FROM, [to_email], msg.as_string())
        
        logger.info(f"Verification email sent to {to_email}")
        return True
        
    except smtplib.SMTPAuthenticationError:
        logger.error(f"SMTP authentication failed for {to_email}")
        return False
    except smtplib.SMTPException as e:
        logger.error(f"SMTP error sending email to {to_email}: {e}")
        return False
    except Exception as e:
        logger.error(f"Error sending email to {to_email}: {e}")
        return False
