from __future__ import annotations

import hashlib
import re
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from typing import Iterable, Optional

from dateutil import parser


def safe_strip(value: Optional[str]) -> str:
    return (value or "").strip()


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def normalize_key(parts: Iterable[str]) -> str:
    joined = "|".join(normalize_space(part).lower() for part in parts if part)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def parse_date(value: Optional[str]) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return _from_timestamp(float(value))
    value = str(value).strip()
    if value.isdigit():
        return _from_timestamp(float(value))
    try:
        return parsedate_to_datetime(value)
    except (TypeError, ValueError):
        pass
    try:
        return parser.parse(value, fuzzy=True)
    except (TypeError, ValueError):
        return None


def _from_timestamp(value: float) -> Optional[datetime]:
    if value > 1e12:
        value = value / 1000
    if value <= 0:
        return None
    return datetime.fromtimestamp(value)


def is_within_days(date_value: Optional[datetime], days: int, now: datetime) -> bool:
    if not date_value:
        return False
    if date_value.tzinfo is None and now.tzinfo is not None:
        date_value = date_value.replace(tzinfo=now.tzinfo)
    return now - timedelta(days=days) <= date_value <= now + timedelta(hours=2)


def hours_ago(date_value: Optional[datetime], now: datetime) -> Optional[float]:
    if not date_value:
        return None
    if date_value.tzinfo is None and now.tzinfo is not None:
        date_value = date_value.replace(tzinfo=now.tzinfo)
    return (now - date_value).total_seconds() / 3600
