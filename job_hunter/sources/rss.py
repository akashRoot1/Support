from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, List
from urllib.parse import quote_plus

from ..http_client import build_session, get_timeout
from ..models import Job
from ..utils import parse_date, normalize_space


class RssSource:
    def __init__(self, name: str, url_template: str, config: Dict) -> None:
        self.name = name
        self.url_template = url_template
        self.config = config
        self.session = build_session(config)
        self.timeout = get_timeout(config)

    def fetch_jobs(self, query: str) -> List[Job]:
        url = self.url_template.format(query=quote_plus(query))
        response = self.session.get(url, timeout=self.timeout)
        response.raise_for_status()
        root = ET.fromstring(response.text)
        items = root.findall(".//item")
        jobs: List[Job] = []
        for item in items:
            title = _text(item, "title")
            link = _text(item, "link")
            description = _text(item, "description")
            pub_date = _text(item, "pubDate")
            posted_date = parse_date(pub_date)
            company, location = _parse_title(title)
            jobs.append(
                Job(
                    title=title or "",
                    company=company or "",
                    location=location or "",
                    link=link or "",
                    source=self.name,
                    posted_date=posted_date,
                    description=description,
                )
            )
        return jobs


def _text(item: ET.Element, tag: str) -> str:
    node = item.find(tag)
    return normalize_space(node.text or "") if node is not None else ""


def _parse_title(title: str) -> tuple[str, str]:
    parts = [part.strip() for part in title.split(" - ") if part.strip()]
    if len(parts) >= 3:
        return parts[1], parts[2]
    if len(parts) == 2:
        return parts[1], ""
    return "", ""
