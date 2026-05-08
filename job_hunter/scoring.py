from __future__ import annotations

from typing import Dict, List, Tuple

from .models import Job, JobMatch


def score_job(job: Job, config: Dict) -> JobMatch:
    candidate = config.get("candidate", {})
    search = config.get("search", {})
    reasons: List[str] = []
    score = 0

    role_keywords = [kw.lower() for kw in candidate.get("open_roles", [])]
    entry_keywords = [kw.lower() for kw in candidate.get("entry_level_keywords", [])]
    visa_keywords = [kw.lower() for kw in candidate.get("visa_friendly_keywords", [])]
    remote_keywords = [kw.lower() for kw in candidate.get("remote_keywords", [])]
    skills = [kw.lower() for kw in candidate.get("skills", [])]
    preferred_locations = [kw.lower() for kw in candidate.get("preferred_locations", [])]

    title_lower = job.title.lower()
    location_lower = job.location.lower()
    description_lower = (job.description or "").lower()

    if any(keyword in title_lower for keyword in role_keywords):
        score += 30
        reasons.append("Role matches target titles")

    if any(keyword in title_lower for keyword in entry_keywords) or any(
        keyword in description_lower for keyword in entry_keywords
    ):
        score += 15
        reasons.append("Entry-level friendly")

    matched_skills = [skill for skill in skills if skill in description_lower]
    job.skills = sorted(set(matched_skills), key=str.lower)
    if matched_skills:
        score += min(30, int(len(matched_skills) / max(1, len(skills)) * 30))
        reasons.append("Skills match")

    if any(keyword in location_lower for keyword in preferred_locations):
        score += 15
        reasons.append("Preferred location")

    if any(keyword in title_lower for keyword in remote_keywords) or any(
        keyword in description_lower for keyword in remote_keywords
    ):
        score += 10
        reasons.append("Remote or hybrid")

    if any(keyword in description_lower for keyword in visa_keywords):
        score += 10
        reasons.append("Visa-friendly wording")

    min_score = int(search.get("min_match_score", 0))
    score = min(100, max(score, 0))

    if score < min_score:
        reasons.append("Below minimum score threshold")

    return JobMatch(job=job, score=score, reasons=reasons)


def should_exclude(job: Job, config: Dict) -> Tuple[bool, str]:
    candidate = config.get("candidate", {})
    excluded_keywords = [kw.lower() for kw in candidate.get("excluded_keywords", [])]
    title_lower = job.title.lower()
    description_lower = (job.description or "").lower()
    for keyword in excluded_keywords:
        if keyword.lower() in title_lower or keyword.lower() in description_lower:
            return True, f"Excluded keyword: {keyword}"
    return False, ""
