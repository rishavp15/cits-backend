import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

from django.conf import settings


class GmailSendError(Exception):
    """Raised when the SMTP service cannot send a message."""


def send_certificate_email(recipient: str, subject: str, body: str, attachment=None, filename: str | None = None):
    """
    Send an email via Gmail SMTP.
    
    Args:
        recipient: Recipient email address
        subject: Email subject
        body: Email body (plain text)
        attachment: Optional PDF bytes to attach
        filename: Optional filename for attachment
    """
    if not recipient:
        raise GmailSendError("Recipient email is required.")

    sender = getattr(settings, "GMAIL_SENDER", None) or getattr(settings, "ADMIN_EMAIL", None)
    if not sender:
        raise GmailSendError("Gmail sender address is not configured.")

    smtp_host = getattr(settings, "SMTP_HOST", "smtp.gmail.com")
    smtp_port = getattr(settings, "SMTP_PORT", 587)
    smtp_username = getattr(settings, "SMTP_USERNAME", None) or sender
    smtp_password = getattr(settings, "SMTP_PASSWORD", None)
    
    if not smtp_password:
        raise GmailSendError("SMTP password is not configured. Please set SMTP_PASSWORD in settings.")

    # Create message
    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = recipient
    msg["Subject"] = subject

    # Add body
    msg.attach(MIMEText(body, "plain"))

    # Add attachment if provided
    if attachment:
        part = MIMEBase("application", "pdf")
        part.set_payload(attachment)
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            f'attachment; filename= {filename or "certificate.pdf"}',
        )
        msg.attach(part)

    try:
        # Create SMTP connection
        server = smtplib.SMTP(smtp_host, smtp_port)
        server.starttls()  # Enable TLS encryption
        server.login(smtp_username, smtp_password)
        
        # Send email
        text = msg.as_string()
        server.sendmail(sender, recipient, text)
        server.quit()
    except smtplib.SMTPAuthenticationError as exc:
        raise GmailSendError(f"SMTP authentication failed: {exc}") from exc
    except smtplib.SMTPException as exc:
        raise GmailSendError(f"SMTP error: {exc}") from exc
    except Exception as exc:
        raise GmailSendError(f"Failed to send email: {exc}") from exc
