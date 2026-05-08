from __future__ import annotations

import smtplib
import time
from email.message import EmailMessage
from typing import Dict

MAX_BACKOFF_SECONDS = 60
BACKOFF_SECONDS = 10


def send_email(
    subject: str,
    body: str,
    email_config: Dict,
    retries: int = 3,
) -> None:
    smtp = email_config.get("smtp", {})
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = email_config.get("from")
    message["To"] = email_config.get("to")
    message.set_content(body)

    host = smtp.get("host")
    port = int(smtp.get("port", 587))
    user = smtp.get("user")
    password = smtp.get("password")
    use_tls = smtp.get("use_tls", True)

    last_error = None
    for attempt in range(1, retries + 1):
        try:
            with smtplib.SMTP(host, port, timeout=30) as server:
                if use_tls:
                    server.starttls()
                if user and password:
                    server.login(user, password)
                server.send_message(message)
            return
        except (smtplib.SMTPException, OSError) as exc:
            last_error = exc
            time.sleep(min(MAX_BACKOFF_SECONDS, attempt * BACKOFF_SECONDS))

    if last_error:
        raise last_error
