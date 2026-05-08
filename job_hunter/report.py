from __future__ import annotations

from datetime import datetime
from typing import Dict, Iterable, List, Tuple

from .models import JobMatch
from .utils import hours_ago


def build_report(
    matches: List[JobMatch],
    config: Dict,
    now: datetime,
    repeated_companies: List[Tuple[str, int]],
    extra_sections: Dict[str, List[str]],
) -> Tuple[str, str]:
    email = config.get("email", {})
    search = config.get("search", {})

    subject_prefix = email.get("subject_prefix", "").strip()
    subject = f"{subject_prefix} - {now:%Y-%m-%d}"
    max_per_section = int(search.get("max_jobs_per_section", 10))

    top_matches = matches[:max_per_section]
    remote_jobs = [match for match in matches if _is_remote(match)][:max_per_section]
    easy_apply = [match for match in matches if match.job.easy_apply][:max_per_section]
    visa_friendly = [match for match in matches if match.job.sponsorship][:max_per_section]
    last_24h = [
        match
        for match in matches
        if hours_ago(match.job.posted_date, now) is not None
        and hours_ago(match.job.posted_date, now) <= search.get("last_24h_hours", 24)
    ][:max_per_section]

    body = []
    body.append(_section("Top 10 Best Matches", top_matches, now))
    body.append(_section("Remote Jobs", remote_jobs, now))
    body.append(_section("Easy Apply Jobs", easy_apply, now))
    body.append(_section("Visa-Friendly Companies", visa_friendly, now))
    body.append(_section("Newly Posted Jobs (Last 24 Hours)", last_24h, now))

    if extra_sections.get("stretch_roles"):
        body.append("\nSuggested Stretch Roles:\n" + "\n".join(extra_sections["stretch_roles"]))

    if repeated_companies:
        trends = "\n".join(f"- {company}: {count} postings in last 7 days" for company, count in repeated_companies)
        body.append(f"\nHiring Trends:\n{trends}")

    if extra_sections.get("keywords"):
        body.append("\nKeywords to Add to CV:\n" + "\n".join(extra_sections["keywords"]))

    if extra_sections.get("certifications"):
        body.append("\nCertifications Mentioned:\n" + "\n".join(extra_sections["certifications"]))

    if extra_sections.get("recruiters"):
        body.append("\nRecruiters & Agencies:\n" + "\n".join(extra_sections["recruiters"]))

    if extra_sections.get("events"):
        body.append("\nNetworking Opportunities:\n" + "\n".join(extra_sections["events"]))

    return subject, "\n".join(section for section in body if section)


def _section(title: str, matches: Iterable[JobMatch], now: datetime) -> str:
    lines = [f"{title}:"]
    if not matches:
        lines.append("- No matching roles found.")
        return "\n".join(lines)
    for match in matches:
        job = match.job
        posted = job.posted_date.strftime("%Y-%m-%d") if job.posted_date else "Unknown"
        reasons = ", ".join(match.reasons[:2]) if match.reasons else "Strong match"
        lines.extend(
            [
                f"- {job.title} | {job.company} | {job.location} | Score: {match.score}/100",
                f"  Posted: {posted} | Easy Apply: {'Yes' if job.easy_apply else 'No'} | Sponsorship: {'Yes' if job.sponsorship else 'No'}",
                f"  Reason: {reasons}",
                f"  Link: {job.link}",
            ]
        )
    return "\n".join(lines)


def _is_remote(match: JobMatch) -> bool:
    location = match.job.location.lower()
    description = (match.job.description or "").lower()
    return "remote" in location or "hybrid" in location or "remote" in description or "hybrid" in description
