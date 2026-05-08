from typing import Any, Dict, List, Tuple
from ..models import Job
from ..http_client import build_session, get_timeout
from ..utils import normalize_space, parse_date


class AtsSource:
    def __init__(self, name: str, boards: List[Dict], config: Dict) -> None:
        self.name = name
        self.boards = boards
        self.config = config
        self.session = build_session(config)
        self.timeout = get_timeout(config)

    def fetch_jobs(self, query: str) -> List[Job]:
        jobs: List[Job] = []
        for board in self.boards:
            provider = (board.get("provider") or "").lower()
            company = board.get("company")
            if not company:
                continue
            if provider == "greenhouse":
                jobs.extend(_fetch_greenhouse(company, self.name, self.session, self.timeout))
            elif provider == "lever":
                jobs.extend(_fetch_lever(company, self.name, self.session, self.timeout))
            elif provider == "workable":
                jobs.extend(_fetch_workable(company, self.name, self.session, self.timeout))
        return jobs


def _fetch_greenhouse(
    company: str, source_name: str, session: Any, timeout: Tuple[float, float]
) -> List[Job]:
    url = f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs?content=true"
    response = session.get(url, timeout=timeout)
    response.raise_for_status()
    data = response.json()
    jobs: List[Job] = []
    for item in data.get("jobs", []):
        jobs.append(
            Job(
                title=normalize_space(item.get("title", "")),
                company=company,
                location=normalize_space((item.get("location") or {}).get("name", "")),
                link=item.get("absolute_url", ""),
                source=source_name,
                posted_date=parse_date(item.get("updated_at")),
                description=item.get("content"),
            )
        )
    return jobs


def _fetch_lever(
    company: str, source_name: str, session: Any, timeout: Tuple[float, float]
) -> List[Job]:
    url = f"https://api.lever.co/v0/postings/{company}?mode=json"
    response = session.get(url, timeout=timeout)
    response.raise_for_status()
    data = response.json()
    jobs: List[Job] = []
    for item in data:
        jobs.append(
            Job(
                title=normalize_space(item.get("text", "")),
                company=company,
                location=normalize_space((item.get("categories") or {}).get("location", "")),
                link=item.get("hostedUrl", ""),
                source=source_name,
                posted_date=parse_date(item.get("createdAt")),
                description=item.get("descriptionPlain"),
            )
        )
    return jobs


def _fetch_workable(
    company: str, source_name: str, session: Any, timeout: Tuple[float, float]
) -> List[Job]:
    url = f"https://{company}.workable.com/api/v1/jobs?state=published"
    response = session.get(url, timeout=timeout)
    response.raise_for_status()
    data = response.json()
    jobs: List[Job] = []
    for item in data.get("jobs", []):
        jobs.append(
            Job(
                title=normalize_space(item.get("title", "")),
                company=company,
                location=normalize_space(item.get("location", {}).get("country", "")),
                link=item.get("url", ""),
                source=source_name,
                posted_date=parse_date(item.get("updated_at")),
                description=item.get("shortcode"),
            )
        )
    return jobs
