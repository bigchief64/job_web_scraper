#!/usr/bin/env python3
"""
Job Radar: local job discovery tool that outputs 10 *fresh* backend-leaning, remote/US-friendly roles.

Sources:
  1) HN "Ask HN: Who is hiring?" (official Firebase API)
  2) YC WorkAtAStartup job listings (static HTML)
  3) ATS JSON endpoints (Greenhouse/Lever/Ashby) via a configurable seed list

Usage:
  python job_radar.py
  python job_radar.py --limit 15
"""

from __future__ import annotations

import argparse
import re
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from html import unescape
from typing import Iterable, List, Optional, Tuple

import requests
from bs4 import BeautifulSoup


# ----------------------------
# Config: tune these to taste
# ----------------------------

POSITIVE_KEYWORDS = {
    # strong matches
    "node": 5,
    "node.js": 5,
    "typescript": 5,
    "go": 4,
    "golang": 4,
    "api": 4,
    "apis": 4,
    "integration": 4,
    "integrations": 4,
    "webhook": 4,
    "webhooks": 4,
    "distributed": 4,
    "microservice": 3,
    "microservices": 3,
    "event-driven": 3,
    "kafka": 3,
    "sqs": 3,
    "queue": 2,
    "queues": 2,
    "aws": 3,
    "postgres": 2,
    "postgresql": 2,
    "redis": 2,
    # role-shaping
    "backend": 4,
    "platform": 3,
    "infrastructure": 3,
    "infra": 2,
    "systems": 2,
}

NEGATIVE_KEYWORDS = {
    "react": -10,
    "next.js": -10,
    "frontend": -10,
    "front-end": -10,
    "ui": -8,
    "ux": -8,
    "designer": -12,
    "design": -6,  # careful: can appear in non-UI contexts, but usually a signal
    "mobile": -10,
    "ios": -10,
    "android": -10,
    "product manager": -12,
    "pm": -6,
}

# We *want* minimal frontend; this doesn't hard-exclude full-stack, but penalizes.
SOFT_NEGATIVE = {
    "full stack": -5,
    "full-stack": -5,
    "frontend work": -6,
    "customer-facing ui": -6,
}

REMOTE_HINTS = [
    "remote",
    "work from home",
    "wfh",
    "anywhere",
    "distributed team",
]

US_HINTS = [
    "united states",
    "u.s.",
    "usa",
    "us only",
    "us-based",
    "us time",
    "us timezone",
]

NOLA_REGION_HINTS = [
    "new orleans",
    "nola",
    "metairie",
    "kenner",
    "gretna",
    "harvey",
    "marrero",
    "westwego",
    "chalmette",
    "arabi",
    "slidell",
    "covington",
    "mandeville",
    "hammond",
    "ponchatoula",
    "laplace",
    "laplace",
    "st. rose",
    "st rose",
    "baton rouge",  # optional: include if you consider it in-region
]

ONSITE_HINTS = [
    "onsite",
    "on-site",
    "in office",
    "in-office",
    "in person",
    "in-person",
    "office-based",
    "office based",
]

HYBRID_HINTS = [
    "hybrid",
    "3 days",
    "4 days",
    "2-3 days",
    "x days in office",
    "days in office",
    "weekly onsite",
]

# SQLite DB for "seen links"
DB_PATH = "job_radar.db"


# ----------------------------
# Models
# ----------------------------


@dataclass(frozen=True)
class Job:
    source: str
    title: str
    company: str
    location: str
    url: str
    snippet: str
    score: float
    remote_ok: bool
    us_ok: bool


# ----------------------------
# Storage
# ----------------------------
NON_US_REMOTE_HINTS = [
    "remote netherlands",
    "remote ireland",
    "remote israel",
    "remote uk",
    "remote sweden",
    "remote estonia",
    "remote europe",
    "remote emea",
    "europe only",
    "emea only",
    "uk only",
    "canada only",
    "india only",
]


def remote_us_eligible(blob: str, location: str) -> bool:
    t = (blob or "").lower()
    loc = (location or "").lower()

    # hard reject obvious non-US remote
    if any(h in t for h in NON_US_REMOTE_HINTS) or any(
        h in loc for h in NON_US_REMOTE_HINTS
    ):
        return False

    # accept explicit US / United States
    if (
        "remote - us" in loc
        or "remote (us" in loc
        or "united states" in t
        or "us-based" in t
    ):
        return True

    # accept "remote" + "US" hints anywhere
    if "remote" in t and (
        "united states" in t or re.search(r"\busa\b|\bu\.s\.\b|\bus\b", t)
    ):
        return True

    return False


def db_init() -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS seen (
          url TEXT PRIMARY KEY,
          first_seen_utc TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


def db_seen(url: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM seen WHERE url = ?", (url,))
    hit = cur.fetchone() is not None
    conn.close()
    return hit


def db_mark_seen(url: str) -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT OR IGNORE INTO seen(url, first_seen_utc) VALUES(?, ?)",
        (url, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    conn.close()


# ----------------------------
# Text utilities
# ----------------------------

_ws = re.compile(r"\s+")


def normalize_text(s: str) -> str:
    return _ws.sub(" ", (s or "").strip())


def html_to_text(html: str) -> str:
    # HN comments are HTML; convert to readable text.
    raw = unescape(html or "")
    soup = BeautifulSoup(raw, "html.parser")
    return normalize_text(soup.get_text(" "))


def score_text(text: str) -> float:
    t = (text or "").lower()
    score = 0.0

    for k, v in POSITIVE_KEYWORDS.items():
        if k in t:
            score += v

    for k, v in NEGATIVE_KEYWORDS.items():
        if k in t:
            score += v

    for k, v in SOFT_NEGATIVE.items():
        if k in t:
            score += v

    return score


def looks_remote(text: str) -> bool:
    t = (text or "").lower()
    return any(h in t for h in REMOTE_HINTS)


def looks_us(text: str) -> bool:
    t = (text or "").lower()
    return any(h in t for h in US_HINTS) or "remote (us" in t or "remote us" in t


def looks_onsite_or_hybrid(text: str) -> bool:
    t = (text or "").lower()
    if any(h in t for h in ONSITE_HINTS):
        return True
    if any(h in t for h in HYBRID_HINTS):
        return True
    return False


def in_nola_region(text: str) -> bool:
    t = (text or "").lower()
    return any(h in t for h in NOLA_REGION_HINTS)


def allow_role_by_location(remote_ok: bool, blob: str) -> bool:
    """
    Rule:
      - allow if remote_ok
      - else allow only if onsite/hybrid AND in NOLA region
      - else reject
    """
    if remote_ok:
        return True

    if looks_onsite_or_hybrid(blob) and in_nola_region(blob):
        return True

    return False


def passes_hard_filters(title: str, text: str) -> bool:
    """Hard reject obvious mismatches."""
    blob = f"{title}\n{text}".lower()

    # Hard reject these
    for bad, weight in NEGATIVE_KEYWORDS.items():
        if weight <= -10 and bad in blob:
            return False

    # Require at least one strong backend signal
    must_have_any = [
        "backend",
        "api",
        "platform",
        "infrastructure",
        "distributed",
        "microservice",
        "integrations",
        "webhook",
        "aws",
    ]
    return any(m in blob for m in must_have_any)


# ----------------------------
# Source 1: HN Who Is Hiring
# ----------------------------

HN_BASE = "https://hacker-news.firebaseio.com/v0"


def hn_find_who_is_hiring_story_id(max_scan: int = 200) -> Optional[int]:
    # Correct endpoint: /v0/askstories.json (NOT /item/askstories.json)
    ids = requests.get(f"{HN_BASE}/askstories.json", timeout=20).json()
    for sid in ids[:max_scan]:
        item = requests.get(f"{HN_BASE}/item/{sid}.json", timeout=20).json()
        if not item:
            continue
        title = (item.get("title") or "").lower()
        if "who is hiring" in title:
            return int(item["id"])
    return None


def hn_iter_jobs(limit_fetch: int = 800):
    story_id = hn_find_who_is_hiring_story_id()
    if not story_id:
        return

    story = requests.get(f"{HN_BASE}/item/{story_id}.json", timeout=20).json()
    kids = story.get("kids", []) or []

    scanned = 0
    for cid in kids:
        if scanned >= limit_fetch:
            break
        scanned += 1

        try:
            c = requests.get(f"{HN_BASE}/item/{cid}.json", timeout=20).json()
        except requests.exceptions.RequestException:
            continue  # <-- key: skip transient TLS/network failures

        if not c or c.get("deleted") or c.get("dead"):
            continue

        text = html_to_text(c.get("text") or "")
        if not text:
            continue

        first_line = text.split("\n", 1)[0]
        parts = [p.strip() for p in re.split(r"\s*\|\s*", first_line)][:4]

        def _clean_hn_token(s: str, max_len: int = 60) -> str:
            s = (s or "").strip()
            # cut off if it starts turning into a paragraph
            for stop in [
                " http",
                "https://",
                ". ",
                " We ",
                " We're ",
                " I’m ",
                " I'm ",
            ]:
                idx = s.find(stop)
                if idx != -1 and idx > 10:
                    s = s[:idx].strip()
                    break
            return s[:max_len].strip()

        parts = [_clean_hn_token(p) for p in parts]
        company = parts[0] if parts else "Unknown"
        p1 = parts[1] if len(parts) > 1 else ""
        p2 = parts[2] if len(parts) > 2 else ""

        title = p1
        location = p2 if p2 else "Unknown"

        if "remote" in p1.lower() and (
            p2.lower()
            in ["full-time", "full time", "contract", "part-time", "part time"]
            or not p2
        ):
            location = p1
            title = "HN Hiring Post (see details)"

        url = f"https://news.ycombinator.com/item?id={cid}"
        yield title, company, location, url, text


# ----------------------------
# Source 2: YC WorkAtAStartup listings (static HTML)
# ----------------------------

WAA_URLS = [
    "https://www.workatastartup.com/jobs",  # engineering default
    "https://www.workatastartup.com/jobs/r/all",  # broader
]


def waa_fetch_jobs(
    pages: List[str] = WAA_URLS,
) -> Iterable[Tuple[str, str, str, str, str]]:
    """
    Yields (title, company, location, url, text_snippet)
    The page contains repeated blocks:
      Company link + Job link + meta line with location/remote
    """
    for url in pages:
        r = requests.get(url, timeout=25)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        # Job links are commonly ycombinator.com job posts
        # We'll find anchors to ycombinator.com that look like job titles.
        for a in soup.find_all("a", href=True):
            href = a["href"]
            title = normalize_text(a.get_text(" "))
            if not title or len(title) < 3:
                continue

            # WorkAtAStartup uses links like https://www.ycombinator.com/jobs/...
            if "ycombinator.com" in href and "/jobs/" in href:
                job_url = (
                    href
                    if href.startswith("http")
                    else f"https://www.ycombinator.com{href}"
                )

                # Attempt to find company + location text around it
                container = a.parent
                # Walk up a bit to capture the surrounding block
                for _ in range(3):
                    if container and container.parent:
                        container = container.parent

                block_text = (
                    normalize_text(container.get_text(" ")) if container else title
                )
                # Company name is usually in the block as "(Batch)" before title; best-effort:
                company = "Unknown"
                m = re.search(
                    r"([A-Za-z0-9][A-Za-z0-9 &\-\.\']+)\s*\(([A-Z]\d{2}|[A-Z]\d{1,2}|[A-Z]\d{2,})\)",
                    block_text,
                )
                if m:
                    company = normalize_text(m.group(1))

                # Location usually includes "Remote" or city/state
                location = "Unknown"
                loc_match = re.search(
                    r"(fulltime|intern)\s+(.+?)(Backend|Full stack|Frontend|Devops|Data|Engineering manager|$)",
                    block_text,
                    flags=re.IGNORECASE,
                )
                if loc_match:
                    location = normalize_text(loc_match.group(2))

                yield title, company, location, job_url, block_text


# ----------------------------
# Source 3: ATS JSON (seed list)
# ----------------------------

# You can add more here over time. This is intentionally small to start.
ATS_SEEDS = {
    # greenhouse boards: https://boards-api.greenhouse.io/v1/boards/{token}/jobs
    "greenhouse": [
        # Examples; replace with companies you care about.
        # "temporal", "datadog", ...
    ],
    # lever: https://api.lever.co/v0/postings/{company}?mode=json
    "lever": [
        # "posthog", "segment", ...
    ],
    # ashby: no simple universal unauth'd JSON; many companies expose JSON via their pages.
    # We'll support Ashby via HTML parsing of ashbyhq job listings (still stable-ish) if you provide company slug.
    "ashby": [
        # "supabase", ...
    ],
}
ATS_SEEDS["greenhouse"] += [
    "tailscale",
    "launchdarkly",
    "doitintl",
    "veeamsoftware",
    "bigid",
    "lithic",
]
ATS_SEEDS["ashby"] += ["cubesoftware", "chromatic", "close", "percona"]
ATS_SEEDS["lever"] += ["zerion", "Anovium"]


def ats_greenhouse_jobs(token: str) -> List[Tuple[str, str, str, str, str]]:
    out = []
    url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs"
    try:
        data = requests.get(url, timeout=20).json()
    except Exception:
        return out

    for j in data.get("jobs", []) or []:
        title = j.get("title") or ""
        job_url = j.get("absolute_url") or ""
        location = (j.get("location") or {}).get("name") or "Unknown"
        company = token
        text = normalize_text(f"{title} {location}")
        if job_url:
            out.append((title, company, location, job_url, text))
    return out


def ats_lever_jobs(company: str) -> List[Tuple[str, str, str, str, str]]:
    out = []
    url = f"https://api.lever.co/v0/postings/{company}?mode=json"
    try:
        data = requests.get(url, timeout=20).json()
    except Exception:
        return out

    for j in data or []:
        title = j.get("text") or ""
        job_url = j.get("hostedUrl") or ""
        location = j.get("categories", {}).get("location") or "Unknown"
        text = normalize_text(
            f"{title} {location} {(j.get('descriptionPlain') or '')[:400]}"
        )
        if job_url:
            out.append((title, company, location, job_url, text))
    return out


def ats_ashby_jobs(company_slug: str) -> List[Tuple[str, str, str, str, str]]:
    """
    Ashby does not provide a simple universal public JSON endpoint.
    Many Ashby boards render a stable HTML page:
      https://jobs.ashbyhq.com/{company_slug}
    We'll parse job links from that page.
    """
    out = []
    url = f"https://jobs.ashbyhq.com/{company_slug}"
    try:
        r = requests.get(url, timeout=25)
        if r.status_code != 200:
            return out
        soup = BeautifulSoup(r.text, "html.parser")
    except Exception:
        return out

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/job/" in href or "/application/" in href:
            title = normalize_text(a.get_text(" "))
            if not title:
                continue
            job_url = (
                href if href.startswith("http") else f"https://jobs.ashbyhq.com{href}"
            )
            # Location often appears nearby; best-effort
            container = a.parent
            for _ in range(2):
                if container and container.parent:
                    container = container.parent
            block = normalize_text(container.get_text(" ")) if container else title
            out.append((title, company_slug, "Unknown", job_url, block))
    return out


def ats_fetch_all() -> Iterable[Tuple[str, str, str, str, str]]:
    for token in ATS_SEEDS.get("greenhouse", []):
        for row in ats_greenhouse_jobs(token):
            yield row
    for company in ATS_SEEDS.get("lever", []):
        for row in ats_lever_jobs(company):
            yield row
    for slug in ATS_SEEDS.get("ashby", []):
        for row in ats_ashby_jobs(slug):
            yield row


# ----------------------------
# Ranking & Output
# ----------------------------


def job_from_raw(
    source: str, title: str, company: str, location: str, url: str, text: str
) -> Optional[Job]:
    blob = f"{title}\n{company}\n{location}\n{text}"
    if not passes_hard_filters(title, blob):
        return None

    score = score_text(blob)
    if score < 2:
        return None

    remote_ok = looks_remote(blob) or ("remote" in (location or "").lower())
    if remote_ok and not remote_us_eligible(blob, location):
        return None
    us_ok = (
        looks_us(blob)
        or ("us" in (location or "").lower())
        or ("united states" in (location or "").lower())
    )

    # ✅ NEW: filter out onsite/hybrid unless NOLA region
    if not allow_role_by_location(remote_ok, blob):
        return None

    snippet = normalize_text(text)[:260]
    return Job(
        source=source,
        title=normalize_text(title),
        company=normalize_text(company or "Unknown"),
        location=normalize_text(location or "Unknown"),
        url=url,
        snippet=snippet,
        score=score,
        remote_ok=remote_ok,
        us_ok=us_ok,
    )


def pick_fresh(jobs: List[Job], limit: int) -> List[Job]:
    fresh = []
    for j in sorted(jobs, key=lambda x: x.score, reverse=True):
        if db_seen(j.url):
            continue
        fresh.append(j)
        if len(fresh) >= limit:
            break
    return fresh


def print_jobs(jobs: List[Job]) -> None:
    for j in jobs:
        flags = []
        if j.remote_ok:
            flags.append("REMOTE")
        if j.us_ok:
            flags.append("US")
        flag_str = " ".join(flags) if flags else "UNKNOWN-REMOTE/US"

        print("\n" + "-" * 72)
        print(f"Score: {j.score:.1f}  [{flag_str}]  Source: {j.source}")
        print(f"Title: {j.title}")
        print(f"Company: {j.company}")
        print(f"Location: {j.location}")
        print(f"URL: {j.url}")
        if j.snippet:
            print(f"Snippet: {j.snippet}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--limit", type=int, default=10, help="How many fresh links to return"
    )
    parser.add_argument(
        "--require-remote",
        action="store_true",
        help="Only output jobs that look remote",
    )
    parser.add_argument(
        "--require-us",
        action="store_true",
        help="Only output jobs that look US-friendly",
    )
    parser.add_argument(
        "--pause",
        type=float,
        default=0.0,
        help="Pause between network calls (seconds) if you want to be gentle",
    )
    args = parser.parse_args()

    db_init()

    collected: List[Job] = []
    hn_count = 0
    yc_count = 0
    ats_count = 0
    # Source A: HN
    try:
        for title, company, location, url, text in hn_iter_jobs():
            if args.pause:
                time.sleep(args.pause)
            j = job_from_raw("HN", title, company, location, url, text)
            if not j:
                continue
            if args.require_remote and not j.remote_ok:
                continue
            if args.require_us and not j.us_ok:
                continue

            seen_title_keys = set()
            key = (j.company.lower(), re.sub(r"\s+", " ", j.title.lower()).strip())
            if key in seen_title_keys:
                continue
            seen_title_keys.add(key)
            collected.append(j)
            hn_count += 1
            if len(collected) >= 200:  # cap
                break
    except Exception as e:
        print(f"[warn] HN source failed: {e}")

    # Source B: WorkAtAStartup listings
    try:
        for title, company, location, url, text in waa_fetch_jobs():
            if args.pause:
                time.sleep(args.pause)
            j = job_from_raw("YC(WaaS)", title, company, location, url, text)
            if not j:
                continue
            if args.require_remote and not j.remote_ok:
                continue
            if args.require_us and not j.us_ok:
                continue

            seen_title_keys = set()
            key = (j.company.lower(), re.sub(r"\s+", " ", j.title.lower()).strip())
            if key in seen_title_keys:
                continue
            seen_title_keys.add(key)

            collected.append(j)
            yc_count += 1
    except Exception as e:
        print(f"[warn] YC WorkAtAStartup source failed: {e}")

    # Source C: ATS seeds (optional until you add slugs/tokens)
    try:
        for title, company, location, url, text in ats_fetch_all():
            if args.pause:
                time.sleep(args.pause)
            j = job_from_raw("ATS", title, company, location, url, text)
            if not j:
                continue
            if args.require_remote and not j.remote_ok:
                continue
            if args.require_us and not j.us_ok:
                continue

            seen_title_keys = set()
            key = (j.company.lower(), re.sub(r"\s+", " ", j.title.lower()).strip())
            if key in seen_title_keys:
                continue
            seen_title_keys.add(key)

            collected.append(j)
            ats_count += 1
    except Exception as e:
        print(f"[warn] ATS source failed: {e}")

    fresh = pick_fresh(collected, args.limit)
    print(
        f"[debug] collected: HN={hn_count} YC={yc_count} ATS={ats_count} total={len(collected)}"
    )

    # If we got too few, relax the US/remote constraints automatically (but keep frontend rejects)
    if len(fresh) < args.limit and (args.require_remote or args.require_us):
        relaxed = pick_fresh(collected, args.limit)
        fresh = relaxed

    if not fresh:
        print("No fresh matches found. Suggestions:")
        print("  - Try: python job_radar.py --limit 10 (no require flags)")
        print(
            "  - Or relax filters; or add ATS seeds (Greenhouse/Lever/Ashby slugs) you care about."
        )
        return 1

    print_jobs(fresh)

    for j in fresh:
        db_mark_seen(j.url)

    print("\n" + "=" * 72)
    print(f"Returned {len(fresh)} fresh jobs. Seen DB: {DB_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
