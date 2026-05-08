from __future__ import annotations

import argparse
import logging
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from zoneinfo import ZoneInfo

import requests

from .config import load_config
from .emailer import send_email
from .models import Job, JobMatch
from .report import build_report
from .scoring import score_job, should_exclude
from .sources import AtsSource, HtmlSource, RssSource
from .storage import Storage
from .utils import is_within_days, normalize_space


DATA_PATH = Path(__file__).resolve().parents[1] / "data"


def main() -> None:
    args = _parse_args()
    config = load_config(args.config)
    run_config = config.get("run", {})

    timezone = ZoneInfo(run_config.get("timezone", "Europe/Dublin"))
    now = datetime.now(tz=timezone)
    logger = _setup_logging(DATA_PATH / "job_hunter.log")

    storage = Storage(DATA_PATH / "jobs.db")
    if not args.force and not _should_run_now(now, run_config, storage):
        storage.close()
        return

    jobs = _collect_jobs(config, logger)
    matches = _filter_and_score(jobs, config, now, storage)
    matches.sort(key=lambda match: (match.score, match.job.posted_date or now), reverse=True)

    repeated_companies = storage.list_recent_companies(7)
    extra_sections = _build_extra_sections(matches, config)
    subject, body = build_report(matches, config, now, repeated_companies, extra_sections)

    run_date = now.strftime("%Y-%m-%d")
    if args.dry_run or run_config.get("dry_run"):
        print(subject)
        print(body)
        storage.close()
        return

    if matches or run_config.get("send_when_empty", True):
        send_email(
            subject,
            body,
            config.get("email", {}),
            retries=int(config.get("email", {}).get("smtp", {}).get("retries", 3)),
        )
    storage.mark_sent([storage.job_id(match.job) for match in matches], now.isoformat())
    storage.record_run(run_date, now.isoformat())
    storage.close()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Daily IT Support job hunter")
    parser.add_argument("--config", default="config/job_hunter.yaml")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true", help="Run even if not scheduled")
    return parser.parse_args()


def _should_run_now(now: datetime, run_config: Dict, storage: Storage) -> bool:
    if storage.has_run_today(now.strftime("%Y-%m-%d")):
        return False
    target_hour = int(run_config.get("target_hour", 5))
    window_minutes = int(run_config.get("window_minutes", 20))
    if now.hour != target_hour:
        return False
    if now.minute > window_minutes:
        return False
    return True


def _collect_jobs(config: Dict, logger: logging.Logger) -> List[Job]:
    search = config.get("search", {})
    queries = search.get("queries", [])
    jobs: List[Job] = []
    for source in config.get("sources", []):
        if not source.get("enabled", True):
            continue
        source_type = source.get("type")
        if source_type == "rss":
            collector = RssSource(source.get("name", "RSS"), source.get("url_template", ""), config)
        elif source_type == "html":
            collector = HtmlSource(
                source.get("name", "HTML"),
                source.get("url_template"),
                source.get("selectors", {}),
                config,
            )
        elif source_type == "ats":
            collector = AtsSource(source.get("name", "ATS"), source.get("ats_boards", []), config)
        else:
            continue

        for query in queries:
            try:
                jobs.extend(collector.fetch_jobs(query))
            except (requests.RequestException, ValueError, ET.ParseError) as exc:
                logger.warning("Source failed: %s (%s) -> %s", collector.name, query, exc)
                continue
    return jobs


def _filter_and_score(jobs: List[Job], config: Dict, now: datetime, storage: Storage) -> List[JobMatch]:
    search = config.get("search", {})
    max_days = int(search.get("max_age_days", 3))
    matches: List[JobMatch] = []
    all_matches: List[JobMatch] = []
    seen_ids = set()
    for job in jobs:
        _annotate_job(job, config)
        if not job.title or not job.link:
            continue
        if not is_within_days(
            job.posted_date,
            max_days,
            now,
            int(search.get("future_hours_tolerance", 2)),
        ):
            continue
        excluded, _ = should_exclude(job, config)
        if excluded:
            continue
        job_id = storage.job_id(job)
        if job_id in seen_ids:
            continue
        seen_ids.add(job_id)
        match = score_job(job, config)
        all_matches.append(match)
        if storage.is_sent(job_id):
            continue
        if match.score < int(search.get("min_match_score", 0)):
            continue
        matches.append(match)

    storage.upsert_jobs(all_matches, now)
    return matches


def _annotate_job(job: Job, config: Dict) -> None:
    candidate = config.get("candidate", {})
    easy_apply_keywords = [kw.lower() for kw in candidate.get("easy_apply_keywords", [])]
    visa_keywords = [kw.lower() for kw in candidate.get("visa_friendly_keywords", [])]
    description = normalize_space(job.description or "").lower()
    title = job.title.lower()
    if any(keyword in description or keyword in title for keyword in easy_apply_keywords):
        job.easy_apply = True
    if any(keyword in description for keyword in visa_keywords):
        job.sponsorship = True


def _build_extra_sections(matches: List[JobMatch], config: Dict) -> Dict[str, List[str]]:
    extra_sections: Dict[str, List[str]] = {}

    stretch = [match for match in matches if 40 <= match.score < 60][:3]
    if stretch:
        extra_sections["stretch_roles"] = [
            f"- {match.job.title} at {match.job.company} ({match.job.location}) -> {match.job.link}"
            for match in stretch
        ]

    tracked_keywords = config.get("data_sources", {}).get("keywords_to_track", [])
    keywords_found = []
    for keyword in tracked_keywords:
        if any(keyword.lower() in (match.job.description or "").lower() for match in matches):
            keywords_found.append(f"- {keyword}")
    if keywords_found:
        extra_sections["keywords"] = keywords_found

    certifications = []
    for cert in ["ITIL", "CompTIA", "Microsoft", "AWS", "Azure", "Cisco"]:
        if any(cert.lower() in (match.job.description or "").lower() for match in matches):
            certifications.append(f"- {cert}")
    if certifications:
        extra_sections["certifications"] = certifications

    recruiters = config.get("data_sources", {}).get("recruiters", [])
    if recruiters:
        extra_sections["recruiters"] = [
            f"- {item.get('name')} | {item.get('website')}"
            + (f" | {item.get('email')}" if item.get("email") else "")
            for item in recruiters
        ]

    events = config.get("data_sources", {}).get("networking_events", [])
    if events:
        extra_sections["events"] = [
            f"- {item.get('name')} | {item.get('website')}"
            + (f" | {item.get('date')}" if item.get("date") else "")
            for item in events
        ]

    return extra_sections


def _setup_logging(log_path: Path) -> logging.Logger:
    logger = logging.getLogger("job_hunter")
    logger.setLevel(logging.INFO)
    if logger.handlers:
        return logger
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    file_handler = logging.FileHandler(log_path)
    file_handler.setFormatter(formatter)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    return logger
