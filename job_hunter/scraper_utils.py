from __future__ import annotations

import html
import re
import sys
from typing import Optional
from urllib.parse import urljoin

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None  # type: ignore[assignment]

try:
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover
    PlaywrightTimeoutError = Exception  # type: ignore[assignment]
    sync_playwright = None  # type: ignore[assignment]


def warn(message: str) -> None:
    print(f"[warn] {message}", file=sys.stderr)


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def strip_tags(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", value)
    return normalize_text(html.unescape(text))


def absolute_url(base_url: str, maybe_relative: str) -> str:
    return urljoin(base_url, maybe_relative)


def fetch_html_with_requests(url: str, timeout: int = 25) -> Optional[str]:
    if requests is None:
        warn("requests is not installed; requests fallback disabled")
        return None

    try:
        response = requests.get(
            url,
            timeout=timeout,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
            },
        )
        if response.status_code >= 400:
            warn(f"requests fallback got HTTP {response.status_code} for {url}")
            return None
        return response.text
    except Exception as exc:  # pragma: no cover
        warn(f"requests fallback failed for {url}: {exc}")
        return None


def fetch_html_with_playwright(url: str, wait_selector: str, timeout_ms: int = 45000) -> Optional[str]:
    if sync_playwright is None:
        warn("playwright is not installed; browser scraping path disabled")
        return None

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            try:
                page.wait_for_selector(wait_selector, timeout=timeout_ms)
            except PlaywrightTimeoutError:
                # Continue with whatever content is available.
                pass
            page.wait_for_timeout(1500)
            content = page.content()
            browser.close()
            return content
    except Exception as exc:  # pragma: no cover
        warn(f"playwright scraping failed for {url}: {exc}")
        return None
