from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class Job:
    title: str
    company: str
    location: str
    link: str
    source: str
    posted_date: Optional[datetime] = None
    salary: Optional[str] = None
    description: Optional[str] = None
    easy_apply: bool = False
    sponsorship: bool = False
    skills: List[str] = field(default_factory=list)

    def normalized_key(self) -> str:
        return "|".join(
            [
                self.title.strip().lower(),
                self.company.strip().lower(),
                self.location.strip().lower(),
                self.link.strip().lower(),
            ]
        )


@dataclass
class JobMatch:
    job: Job
    score: int
    reasons: List[str] = field(default_factory=list)
