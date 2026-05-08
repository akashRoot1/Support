from __future__ import annotations

from typing import Dict, List, Optional
from urllib.parse import quote_plus, urljoin

from bs4 import BeautifulSoup

from ..http_client import build_session, get_timeout
from ..models import Job
from ..utils import normalize_space, parse_date


class HtmlSource:
    def __init__(self, name: str, url_template: Optional[str], selectors: Dict, config: Dict) -> None:
        self.name = name
        self.url_template = url_template
        self.selectors = selectors or {}
        self.config = config
        self.session = build_session(config)
        self.timeout = get_timeout(config)

    def fetch_jobs(self, query: str) -> List[Job]:
        if not self.url_template:
            return []
        url = self.url_template.format(query=quote_plus(query))
        response = self.session.get(url, timeout=self.timeout)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        card_selector = self.selectors.get("job_card")
        cards = soup.select(card_selector) if card_selector else []
        jobs: List[Job] = []
        for card in cards:
            title = _select_text(card, self.selectors.get("title"))
            company = _select_text(card, self.selectors.get("company"))
            location = _select_text(card, self.selectors.get("location"))
            link = _select_attr(card, self.selectors.get("link"), "href")
            date_text = _select_text(card, self.selectors.get("date"))
            snippet = _select_text(card, self.selectors.get("snippet"))
            if link:
                link = urljoin(url, link)
            jobs.append(
                Job(
                    title=title or "",
                    company=company or "",
                    location=location or "",
                    link=link or "",
                    source=self.name,
                    posted_date=parse_date(date_text),
                    description=snippet,
                )
            )
        return jobs


def _select_text(node, selector: Optional[str]) -> str:
    if not selector:
        return ""
    target = node.select_one(selector)
    return normalize_space(target.get_text(strip=True)) if target else ""


def _select_attr(node, selector: Optional[str], attr: str) -> str:
    if not selector:
        return ""
    target = node.select_one(selector)
    if not target:
        return ""
    return normalize_space(target.get(attr) or "")
