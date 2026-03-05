from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def init_db(db_path: str = "jobs_seen.db") -> None:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs_seen(
                url TEXT PRIMARY KEY,
                first_seen TIMESTAMP NOT NULL
            )
            """
        )
        conn.commit()


def job_seen(url: str, db_path: str = "jobs_seen.db") -> bool:
    with sqlite3.connect(db_path) as conn:
        row = conn.execute("SELECT 1 FROM jobs_seen WHERE url = ? LIMIT 1", (url,)).fetchone()
    return row is not None


def mark_job_seen(url: str, db_path: str = "jobs_seen.db") -> None:
    timestamp = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO jobs_seen(url, first_seen) VALUES (?, ?)",
            (url, timestamp),
        )
        conn.commit()
