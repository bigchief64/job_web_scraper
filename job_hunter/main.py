from __future__ import annotations

import argparse
from typing import List

from .models import Job
from .pipeline import collect_fresh_jobs


DEFAULT_LIMIT = 10
DEFAULT_DB_PATH = "jobs_seen.db"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Discover fresh backend jobs from YC and Wellfound")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help="Max fresh jobs to print (default: 10)")
    parser.add_argument("--dry-run", action="store_true", help="Run without marking jobs as seen")
    parser.add_argument("--db-path", default=DEFAULT_DB_PATH, help="SQLite path for seen job tracking")
    return parser


def format_job(job: Job) -> str:
    score = f"{job.score:.1f}"
    source = "YC" if job.source == "yc" else "Wellfound" if job.source == "wellfound" else job.source
    location = job.location
    if job.remote_label == "unknown":
        location = f"{location} (remote unknown)"
    return (
        f"Score: {score}\n"
        f"Title: {job.title}\n"
        f"Company: {job.company}\n"
        f"Location: {location}\n"
        f"Source: {source}\n"
        f"URL: {job.url}\n"
    )


def run(limit: int, dry_run: bool, db_path: str) -> List[Job]:
    jobs = collect_fresh_jobs(limit=limit, dry_run=dry_run, db_path=db_path)
    for job in jobs:
        print(format_job(job))
    if not jobs:
        print("No fresh jobs found.")
    return jobs


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.limit <= 0:
        parser.error("--limit must be positive")

    run(limit=args.limit, dry_run=args.dry_run, db_path=args.db_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
