"""Mailer with three modes. $0 dev default is 'console'; SMTP via env vars.

Never raises: delivery failures are logged, not fatal.
"""
import logging
import smtplib
from email.message import EmailMessage

from app.core.config import get_settings

log = logging.getLogger(__name__)


def send_email(to_email: str, subject: str, body: str) -> bool:
    settings = get_settings()
    mode = settings.MAIL_MODE.lower()
    try:
        if mode == "smtp" and settings.SMTP_HOST:
            msg = EmailMessage()
            msg["From"] = settings.SMTP_FROM
            msg["To"] = to_email
            msg["Subject"] = subject
            msg.set_content(body)
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as s:
                s.starttls()
                if settings.SMTP_USER:
                    s.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                s.send_message(msg)
            log.info("email sent via smtp subject=%s", subject)
        elif mode == "file":
            with open(settings.MAIL_FILE_PATH, "a", encoding="utf-8") as f:
                f.write(f"---\nTO: {to_email}\nSUBJECT: {subject}\n{body}\n")
            log.info("email written to file outbox subject=%s", subject)
        else:  # console
            print(f"[MAIL to={to_email}] subject={subject}\n{body}\n", flush=True)
            log.info("email printed to console subject=%s", subject)
        return True
    except Exception as exc:  # never fatal
        log.warning("email delivery failed mode=%s err=%s", mode, exc)
        return False


def verification_email_body(token: str) -> str:
    return (
        "Verify your email address with this token (expires in 24 hours):\n\n"
        f"{token}\n\n"
        "Enter it in the app's Verify Email screen."
    )


def verification_code_email_body(code: str) -> str:
    return (
        "Your email verification code (expires in 10 minutes):\n\n"
        f"{code}\n\n"
        "Enter this 6-digit code in the app's Verify Email screen.\n"
        "If you did not request this, ignore this message."
    )


def password_reset_email_body(token: str) -> str:
    return (
        "Reset your password with this token (single-use, expires in 1 hour):\n\n"
        f"{token}\n\n"
        "If you did not request this, ignore this message."
    )
