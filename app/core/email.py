import logging
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OutgoingEmail:
    to: str
    subject: str
    body: str


def send_email(email: OutgoingEmail) -> None:
    if not settings.smtp_host:
        logger.warning("SMTP not configured, email not sent:\nTo: %s\nSubject: %s\n\n%s",
                       email.to, email.subject, email.body)
        return

    message = EmailMessage()
    message["From"] = settings.mail_from
    message["To"] = email.to
    message["Subject"] = email.subject
    message.set_content(email.body)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
        if settings.smtp_user:
            smtp.starttls()
            smtp.login(settings.smtp_user, settings.smtp_password or "")
        smtp.send_message(message)
