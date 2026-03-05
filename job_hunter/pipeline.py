from __future__ import annotations

import sys
from typing import List

from .filters import is_relevant_job
from .models import Job
from .scoring import score_job
from .storage import init_db, job_seen, mark_job_seen
from .wellfound_scraper import scrape_wellfound_jobs
from .yc_scraper import scrape_yc_jobs


def _safe_scrape(name: str, fn) -> List[Job]:
    try:
        return fn()
    except Exception as exc:  # pragma: no cover
        print(f"[warn] scraper {name} failed: {exc}", file=sys.stderr)
        return []


def _remote_priority(job: Job) -> int:
    if job.remote_label == "remote-us":
        return 3
    if job.remote_label == "remote-friendly":
        return 2
    if job.remote_label == "remote":
        return 1
    return 0


def collect_fresh_jobs(limit: int, dry_run: bool, db_path: str) -> List[Job]:
    init_db(db_path)

    scraped_jobs = _safe_scrape("yc", scrape_yc_jobs) + _safe_scrape("wellfound", scrape_wellfound_jobs)
    candidates: List[Job] = []
    urls_in_run: set[str] = set()

    for job in scraped_jobs:
        if not job.url or job.url in urls_in_run:
            continue
        urls_in_run.add(job.url)
        if not is_relevant_job(job):
            continue
        if score_job(job) < 0:
            continue
        if job_seen(job.url, db_path=db_path):
            continue
        candidates.append(job)

    candidates.sort(key=lambda job: (_remote_priority(job), job.score), reverse=True)
    selected = candidates[:limit]

    if not dry_run:
        for job in selected:
            mark_job_seen(job.url, db_path=db_path)

    return selected
