import sqlite3

DB = "hn_jobs.db"

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS seen_jobs(
        id INTEGER PRIMARY KEY
    )
    """)

    conn.commit()
    conn.close()


def seen(job_id):

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT 1 FROM seen_jobs WHERE id=?", (job_id,))
    r = c.fetchone()

    conn.close()

    return r is not None


def mark_seen(job_id):

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("INSERT OR IGNORE INTO seen_jobs VALUES (?)", (job_id,))
    conn.commit()

    conn.close()