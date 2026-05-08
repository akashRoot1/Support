from __future__ import annotations

import os
from typing import Any, Dict

import yaml


def load_config(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle) or {}

    email = config.setdefault("email", {})
    smtp = email.setdefault("smtp", {})

    email["to"] = os.getenv("EMAIL_TO", email.get("to", ""))
    email["from"] = os.getenv("EMAIL_FROM", email.get("from", ""))
    smtp["host"] = os.getenv("SMTP_HOST", smtp.get("host", ""))
    smtp_port = os.getenv("SMTP_PORT")
    if smtp_port is None or not smtp_port.strip():
        smtp["port"] = int(smtp.get("port", 587))
    else:
        smtp["port"] = int(smtp_port)
    smtp["user"] = os.getenv("SMTP_USER", smtp.get("user", ""))
    smtp["password"] = os.getenv("SMTP_PASS", smtp.get("password", ""))

    run = config.setdefault("run", {})
    if os.getenv("DRY_RUN", "").lower() in {"1", "true", "yes"}:
        run["dry_run"] = True

    return config
