from __future__ import annotations

from typing import Dict, Iterable, List, Tuple

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome Safari/537.36"
)

DEFAULT_HEADERS = {
    "User-Agent": DEFAULT_USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json;q=0.8,*/*;q=0.7",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}

DEFAULT_CONNECT_TIMEOUT = 10.0
DEFAULT_READ_TIMEOUT = 40.0
DEFAULT_RETRY_TOTAL = 1
DEFAULT_BACKOFF_FACTOR = 0.5
DEFAULT_STATUS_FORCELIST = [429, 500, 502, 503, 504]
DEFAULT_ALLOWED_METHODS = ["GET"]


def build_session(config: Dict) -> requests.Session:
    session = requests.Session()
    session.headers.update(build_headers(config))

    retry_config = _get_http_config(config).get("retries", {}) or {}
    total = _coerce_int(retry_config.get("total"), DEFAULT_RETRY_TOTAL)
    if total < 0:
        total = DEFAULT_RETRY_TOTAL
    backoff_factor = _coerce_float(retry_config.get("backoff_factor"), DEFAULT_BACKOFF_FACTOR)
    status_forcelist = _coerce_int_list(
        retry_config.get("status_forcelist"), DEFAULT_STATUS_FORCELIST
    )
    allowed_methods = _coerce_str_list(retry_config.get("allowed_methods"), DEFAULT_ALLOWED_METHODS)

    retry = Retry(
        total=total,
        connect=total,
        read=total,
        status=total,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        allowed_methods=[method.upper() for method in allowed_methods],
        raise_on_status=False,
        respect_retry_after_header=True,
    )

    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def build_headers(config: Dict) -> Dict[str, str]:
    headers = dict(DEFAULT_HEADERS)
    http_config = _get_http_config(config)
    user_agent = http_config.get("user_agent")
    if user_agent:
        headers["User-Agent"] = str(user_agent)
    extra_headers = http_config.get("headers", {})
    if isinstance(extra_headers, dict):
        for key, value in extra_headers.items():
            if value is not None and value != "":
                headers[str(key)] = str(value)
    return headers


def get_timeout(config: Dict) -> Tuple[float, float]:
    http_config = _get_http_config(config)
    timeout_seconds = http_config.get("timeout_seconds")
    if timeout_seconds is not None:
        timeout_value = _coerce_float(timeout_seconds, DEFAULT_READ_TIMEOUT)
        timeout_value = max(timeout_value, 0.0)
        return (timeout_value, timeout_value)
    connect_timeout = _coerce_float(
        http_config.get("connect_timeout_seconds"), DEFAULT_CONNECT_TIMEOUT
    )
    read_timeout = _coerce_float(http_config.get("read_timeout_seconds"), DEFAULT_READ_TIMEOUT)
    return (max(connect_timeout, 0.0), max(read_timeout, 0.0))


def _get_http_config(config: Dict) -> Dict:
    return (config or {}).get("http", {}) or {}


def _coerce_float(value, fallback: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _coerce_int(value, fallback: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _coerce_int_list(value, fallback: List[int]) -> List[int]:
    if not isinstance(value, Iterable) or isinstance(value, (str, bytes, dict)):
        return list(fallback)
    output: List[int] = []
    for item in value:
        try:
            output.append(int(item))
        except (TypeError, ValueError):
            continue
    return output or list(fallback)


def _coerce_str_list(value, fallback: List[str]) -> List[str]:
    if not isinstance(value, Iterable) or isinstance(value, (str, bytes, dict)):
        return list(fallback)
    output: List[str] = []
    for item in value:
        if item:
            output.append(str(item))
    return output or list(fallback)
