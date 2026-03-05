from __future__ import annotations

import re
from html import unescape
from typing import Iterable, List, Optional
from urllib.parse import urlparse

from .models import Job
from .scraper_utils import absolute_url, fetch_html_with_playwright, fetch_html_with_requests, normalize_text, strip_tags

try:
    from bs4 import BeautifulSoup
except ImportError:  # pragma: no cover
    BeautifulSoup = None  # type: ignore[assignment]

WELLFOUND_JOBS_URL = "https://wellfound.com/jobs"
WELLFOUND_BASE_URL = "https://wellfound.com"

REMOTE_PATTERN = re.compile(r"\bremote(?:[-\s]*(friendly|us|usa|united states))?\b", re.IGNORECASE)
CITY_STATE_PATTERN = re.compile(r"\b([A-Za-z .'-]+,\s*[A-Z]{2})\b")


def _is_job_href(href: str) -> bool:
    if not href:
        return False
    if href.startswith("mailto:") or href.startswith("javascript:"):
        return False

    parsed = urlparse(absolute_url(WELLFOUND_BASE_URL, href))
    path = parsed.path.rstrip("/")
    if "/jobs" not in path:
        return False

    segments = [segment for segment in path.split("/") if segment]
    if len(segments) < 2:
        return False

    banned_last = {"jobs", "new", "search", "feed", "discover"}
    if segments[-1].lower() in banned_last:
        return False

    return "jobs" in [segment.lower() for segment in segments]


def _extract_location(text: str) -> str:
    remote = REMOTE_PATTERN.search(text)
    if remote:
        token = remote.group(0)
        return normalize_text(token)

    match = CITY_STATE_PATTERN.search(text)
    if match:
        return normalize_text(match.group(1))
    return "Unknown"


def _is_remote_hint(value: str) -> Optional[bool]:
    lowered = value.lower()
    if "remote" in lowered:
        return True
    if any(token in lowered for token in ("onsite", "on-site", "in-office", "hybrid")):
        return False
    return None


def _job_from_parts(title: str, company: str, location: str, description: str, url: str) -> Job:
    remote_flag = _is_remote_hint(f"{location} {description}")
    return Job(
        title=normalize_text(title) or "Unknown Title",
        company=normalize_text(company) or "Unknown Company",
        location=normalize_text(location) or "Unknown",
        is_remote=remote_flag,
        description=normalize_text(description),
        url=url,
        source="wellfound",
    )


def _parse_with_bs4(html_text: str) -> List[Job]:
    if BeautifulSoup is None:
        return []

    soup = BeautifulSoup(html_text, "html.parser")
    jobs: List[Job] = []
    seen_urls: set[str] = set()

    for anchor in soup.select("a[href*='/jobs/']"):
        href = anchor.get("href", "")
        if not _is_job_href(href):
            continue

        job_url = absolute_url(WELLFOUND_BASE_URL, href)
        if job_url in seen_urls:
            continue

        title = anchor.get_text(" ", strip=True)
        if len(title) < 3:
            continue

        container = anchor
        for _ in range(10):
            parent = container.parent
            if parent is None:
                break
            parent_text = parent.get_text(" ", strip=True)
            if len(parent_text) > 80:
                container = parent
            if "remote" in parent_text.lower() and len(parent_text) > 120:
                break

        company_anchor = None
        if getattr(container, "select_one", None):
            company_anchor = container.select_one("a[href*='/company/'], a[href*='/companies/']")
        company = company_anchor.get_text(" ", strip=True) if company_anchor else "Unknown Company"

        text_blob = container.get_text(" ", strip=True) if getattr(container, "get_text", None) else title
        location = _extract_location(text_blob)

        jobs.append(_job_from_parts(title, company, location, text_blob, job_url))
        seen_urls.add(job_url)

    return jobs


def _iter_regex_matches(html_text: str) -> Iterable[re.Match[str]]:
    pattern = re.compile(
        r"<a[^>]*href=[\"'](?P<href>[^\"']*/jobs/[^\"']+)[\"'][^>]*>(?P<title>.*?)</a>",
        re.IGNORECASE | re.DOTALL,
    )
    return pattern.finditer(html_text)


def _parse_with_regex(html_text: str) -> List[Job]:
    jobs: List[Job] = []
    seen_urls: set[str] = set()

    for match in _iter_regex_matches(html_text):
        raw_href = unescape(match.group("href"))
        if not _is_job_href(raw_href):
            continue

        title = strip_tags(match.group("title"))
        if len(title) < 3:
            continue

        job_url = absolute_url(WELLFOUND_BASE_URL, raw_href)
        if job_url in seen_urls:
            continue

        start = max(match.start() - 1500, 0)
        end = min(match.end() + 1500, len(html_text))
        chunk = html_text[start:end]
        text_chunk = strip_tags(chunk)

        company_match = re.search(
            r"<a[^>]*href=[\"'][^\"']*/compan(?:y|ies)/[^\"']+[\"'][^>]*>(?P<company>.*?)</a>",
            chunk,
            re.IGNORECASE | re.DOTALL,
        )
        company = strip_tags(company_match.group("company")) if company_match else "Unknown Company"

        location = _extract_location(text_chunk)
        jobs.append(_job_from_parts(title, company, location, text_chunk, job_url))
        seen_urls.add(job_url)

    return jobs


def scrape_wellfound_jobs() -> List[Job]:
    html_text = fetch_html_with_playwright(WELLFOUND_JOBS_URL, "a[href*='/jobs/']")
    if not html_text:
        html_text = fetch_html_with_requests(WELLFOUND_JOBS_URL)
    if not html_text:
        return []

    jobs = _parse_with_bs4(html_text)
    if jobs:
        return jobs

    return _parse_with_regex(html_text)
