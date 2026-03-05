from __future__ import annotations

import re
from html import unescape
from typing import Iterable, List, Optional

from .models import Job
from .scraper_utils import absolute_url, fetch_html_with_playwright, fetch_html_with_requests, normalize_text, strip_tags

try:
    from bs4 import BeautifulSoup
except ImportError:  # pragma: no cover
    BeautifulSoup = None  # type: ignore[assignment]

YC_JOBS_URL = "https://www.workatastartup.com/jobs"
YC_BASE_URL = "https://www.workatastartup.com"

REMOTE_LOCATION_PATTERN = re.compile(r"\bremote(?:[\s-]*(us|usa|united states|friendly))?\b", re.IGNORECASE)
CITY_STATE_PATTERN = re.compile(r"\b([A-Z][A-Za-z.'-]+(?:\s+[A-Z][A-Za-z.'-]+){0,3},\s*[A-Z]{2})\b")


def _extract_location(text: str) -> str:
    remote_match = REMOTE_LOCATION_PATTERN.search(text)
    if remote_match:
        return normalize_text(remote_match.group(0))

    city_match = CITY_STATE_PATTERN.search(text)
    if city_match:
        return normalize_text(city_match.group(1))
    return "Unknown"


def _is_remote_hint(value: str) -> Optional[bool]:
    text = value.lower()
    if "remote" in text:
        return True
    if any(token in text for token in ("onsite", "on-site", "hybrid", "in-office")):
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
        source="yc",
    )


def _parse_with_bs4(html_text: str) -> List[Job]:
    if BeautifulSoup is None:
        return []

    soup = BeautifulSoup(html_text, "html.parser")
    jobs: List[Job] = []
    seen_urls: set[str] = set()

    anchors = soup.select("a[data-jobid][href*='ycombinator.com/companies/'][href*='/jobs/']")
    for anchor in anchors:
        href = anchor.get("href", "")
        if not href:
            continue
        job_url = absolute_url(YC_BASE_URL, href)
        if job_url in seen_urls:
            continue

        title = anchor.get_text(" ", strip=True)
        container = anchor
        for _ in range(8):
            parent = container.parent
            if parent is None:
                break
            if getattr(parent, "select_one", None) and parent.select_one("a[target='company']"):
                container = parent
                break
            container = parent

        company_anchor = container.select_one("a[target='company'] .font-bold") if getattr(container, "select_one", None) else None
        company_text = company_anchor.get_text(" ", strip=True) if company_anchor else ""
        company_text = re.sub(r"\s*\([A-Z]\d+\)\s*$", "", company_text)

        container_text = container.get_text(" ", strip=True) if getattr(container, "get_text", None) else ""
        location = _extract_location(container_text)
        description = container_text

        jobs.append(_job_from_parts(title, company_text, location, description, job_url))
        seen_urls.add(job_url)

    return jobs


def _iter_regex_matches(html_text: str) -> Iterable[re.Match[str]]:
    pattern = re.compile(
        r"<a[^>]*data-jobid=[\"'][^\"']+[\"'][^>]*href=[\"'](?P<href>[^\"']+/jobs/[^\"']+)[\"'][^>]*>(?P<title>.*?)</a>",
        re.IGNORECASE | re.DOTALL,
    )
    return pattern.finditer(html_text)


def _parse_with_regex(html_text: str) -> List[Job]:
    jobs: List[Job] = []
    seen_urls: set[str] = set()

    for match in _iter_regex_matches(html_text):
        href = unescape(match.group("href"))
        title = strip_tags(match.group("title"))
        job_url = absolute_url(YC_BASE_URL, href)

        if job_url in seen_urls:
            continue

        start = max(match.start() - 1500, 0)
        end = min(match.end() + 1500, len(html_text))
        chunk = html_text[start:end]

        company_match = re.search(
            r"target=[\"']company[\"'][^>]*>.*?<span[^>]*class=[\"'][^\"']*font-bold[^\"']*[\"'][^>]*>(.*?)</span>",
            chunk,
            re.IGNORECASE | re.DOTALL,
        )
        company = strip_tags(company_match.group(1)) if company_match else "Unknown Company"
        company = re.sub(r"\s*\([A-Z]\d+\)\s*$", "", company)

        text_chunk = strip_tags(chunk)
        location = _extract_location(text_chunk)

        jobs.append(_job_from_parts(title, company, location, text_chunk, job_url))
        seen_urls.add(job_url)

    return jobs


def scrape_yc_jobs() -> List[Job]:
    html_text = fetch_html_with_playwright(YC_JOBS_URL, "a[data-jobid]")
    if not html_text:
        html_text = fetch_html_with_requests(YC_JOBS_URL)
    if not html_text:
        return []

    jobs = _parse_with_bs4(html_text)
    if jobs:
        return jobs

    return _parse_with_regex(html_text)
