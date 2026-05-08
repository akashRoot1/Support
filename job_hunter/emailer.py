from __future__ import annotations

import smtplib
import time
from email.message import EmailMessage
from typing import Any, Dict, Optional

MAX_BACKOFF_SECONDS = 60
BACKOFF_SECONDS = 10


def _is_empty_or_whitespace(value: Optional[str]) -> bool:
    return value is None or not value.strip()


def _validate_email_config(email_config: Dict[str, Any]) -> None:
    smtp = email_config.get("smtp", {})
    missing = []
    if _is_empty_or_whitespace(email_config.get("from")):
        missing.append("EMAIL_FROM/email.from")
    if _is_empty_or_whitespace(email_config.get("to")):
        missing.append("EMAIL_TO/email.to")
    if _is_empty_or_whitespace(smtp.get("host")):
        missing.append("SMTP_HOST/email.smtp.host")
    if _is_empty_or_whitespace(smtp.get("user")):
        missing.append("SMTP_USER/email.smtp.user")
    if _is_empty_or_whitespace(smtp.get("password")):
        missing.append("SMTP_PASS/email.smtp.password")
    if missing:
        raise ValueError(
            f"Missing required email/SMTP settings: {', '.join(missing)}. "
            "Update config/job_hunter.yaml (repo root) or repository secrets."
        )


def send_email(
    subject: str,
    body: str,
    email_config: Dict,
    retries: int = 3,
) -> None:
    _validate_email_config(email_config)
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
        except smtplib.SMTPAuthenticationError as exc:
            raise ValueError(
                "SMTP authentication failed. Verify SMTP_USER/SMTP_PASS (Gmail requires an app password) "
                "and update repository secrets or config/job_hunter.yaml."
            ) from exc
        except (smtplib.SMTPException, OSError) as exc:
            last_error = exc
            time.sleep(min(MAX_BACKOFF_SECONDS, attempt * BACKOFF_SECONDS))

    if last_error:
        raise last_error
