from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

from .models import Job, JobMatch
from .utils import normalize_key


class Storage:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        cursor = self.conn.cursor()
        cursor.executescript(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                title TEXT,
                company TEXT,
                location TEXT,
                link TEXT,
                source TEXT,
                posted_date TEXT,
                salary TEXT,
                easy_apply INTEGER,
                sponsorship INTEGER,
                skills TEXT,
                match_score INTEGER,
                first_seen TEXT,
                last_seen TEXT
            );
            CREATE TABLE IF NOT EXISTS sent_jobs (
                job_id TEXT PRIMARY KEY,
                sent_at TEXT
            );
            CREATE TABLE IF NOT EXISTS runs (
                run_date TEXT PRIMARY KEY,
                run_at TEXT
            );
            """
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def has_run_today(self, run_date: str) -> bool:
        cursor = self.conn.execute("SELECT 1 FROM runs WHERE run_date = ?", (run_date,))
        return cursor.fetchone() is not None

    def record_run(self, run_date: str, run_at: str) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO runs (run_date, run_at) VALUES (?, ?)",
            (run_date, run_at),
        )
        self.conn.commit()

    def is_sent(self, job_id: str) -> bool:
        cursor = self.conn.execute("SELECT 1 FROM sent_jobs WHERE job_id = ?", (job_id,))
        return cursor.fetchone() is not None

    def mark_sent(self, job_ids: Iterable[str], sent_at: str) -> None:
        self.conn.executemany(
            "INSERT OR REPLACE INTO sent_jobs (job_id, sent_at) VALUES (?, ?)",
            [(job_id, sent_at) for job_id in job_ids],
        )
        self.conn.commit()

    def upsert_jobs(self, matches: Iterable[JobMatch], now: datetime) -> None:
        rows = []
        for match in matches:
            job = match.job
            job_id = normalize_key([job.title, job.company, job.location, job.link])
            rows.append(
                (
                    job_id,
                    job.title,
                    job.company,
                    job.location,
                    job.link,
                    job.source,
                    _to_utc_string(job.posted_date),
                    job.salary,
                    int(job.easy_apply),
                    int(job.sponsorship),
                    ", ".join(job.skills),
                    match.score,
                    now.isoformat(),
                    now.isoformat(),
                )
            )
        self.conn.executemany(
            """
            INSERT INTO jobs (
                job_id, title, company, location, link, source, posted_date, salary,
                easy_apply, sponsorship, skills, match_score, first_seen, last_seen
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(job_id) DO UPDATE SET
                last_seen=excluded.last_seen,
                match_score=excluded.match_score,
                posted_date=excluded.posted_date,
                salary=excluded.salary,
                easy_apply=excluded.easy_apply,
                sponsorship=excluded.sponsorship,
                skills=excluded.skills
            """,
            rows,
        )
        self.conn.commit()

    def list_recent_companies(self, days: int) -> list[tuple[str, int]]:
        cursor = self.conn.execute(
            f"""
            SELECT company, COUNT(*) as total
            FROM jobs
            WHERE posted_date IS NOT NULL
              AND datetime(posted_date) >= datetime('now', '-{days} days')
            GROUP BY company
            ORDER BY total DESC
            LIMIT 10
            """
        )
        return [(row["company"], row["total"]) for row in cursor.fetchall()]

    def load_sent_dates(self) -> dict[str, str]:
        cursor = self.conn.execute("SELECT job_id, sent_at FROM sent_jobs")
        return {row["job_id"]: row["sent_at"] for row in cursor.fetchall()}

    def job_id(self, job: Job) -> str:
        return normalize_key([job.title, job.company, job.location, job.link])


def _to_utc_string(value: Optional[datetime]) -> Optional[str]:
    if not value:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    value = value.astimezone(timezone.utc)
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")
