from __future__ import annotations

import re

from .models import Job

BACKEND_SIGNALS = [
    "backend",
    "node",
    "typescript",
    "go",
    "golang",
    "python",
    "api",
    "apis",
    "microservices",
    "distributed",
    "aws",
    "sqs",
    "queue",
    "queues",
    "event-driven",
    "backend platform",
]

HARD_REJECT_TERMS = []

UI_REJECT_PATTERN = re.compile(r"\bui\b", re.IGNORECASE)
FULL_STACK_PATTERN = re.compile(r"full[\s-]?stack", re.IGNORECASE)
TITLE_REQUIRED_HINTS = [
    "engineer",
    "developer",
    "backend",
    "platform",
    "infrastructure",
]
TITLE_REJECT_HINTS = [
    "product",
    "designer",
    "sales",
    "support",
    "marketing",
    "recruit",
    "customer success",
]

REMOTE_US_PATTERNS = [
    re.compile(r"remote[\s-]*(us|usa|united states)", re.IGNORECASE),
    re.compile(r"(us|usa|united states)[\s-]*remote", re.IGNORECASE),
]
REMOTE_FRIENDLY_PATTERNS = [
    re.compile(r"remote[\s-]?friendly", re.IGNORECASE),
]
REMOTE_PATTERN = re.compile(r"\bremote\b", re.IGNORECASE)
HYBRID_PATTERNS = [
    re.compile(r"\bhybrid\b", re.IGNORECASE),
]
ONSITE_PATTERNS = [
    re.compile(r"\bon[\s-]?site\b", re.IGNORECASE),
    re.compile(r"\bin[\s-]?office\b", re.IGNORECASE),
]
CONFIRMED_REMOTE_LABELS = {"remote", "remote-friendly", "remote-us"}

# New Orleans region aliases used by the strict location eligibility policy.
NEW_ORLEANS_REGION_TERMS = [
    "new orleans",
    "metairie",
    "kenner",
    "gretna",
    "harvey",
    "marrero",
    "westwego",
    "chalmette",
    "laplace",
    "slidell",
    "jefferson parish",
    "orleans parish",
    "st. tammany parish",
    "saint tammany parish",
]


def classify_remote(job: Job) -> tuple[str, bool | None]:
    remote_text = f"{job.location}\n{job.title}\n{job.description}".lower()

    if any(pattern.search(remote_text) for pattern in REMOTE_US_PATTERNS):
        return "remote-us", True
    if any(pattern.search(remote_text) for pattern in REMOTE_FRIENDLY_PATTERNS):
        return "remote-friendly", True
    if REMOTE_PATTERN.search(remote_text):
        return "remote", True
    if any(pattern.search(remote_text) for pattern in HYBRID_PATTERNS):
        return "hybrid", False
    if any(pattern.search(remote_text) for pattern in ONSITE_PATTERNS):
        return "onsite", False
    return "unknown", None


def _is_new_orleans_region(job: Job) -> bool:
    location_text = f"{job.location}\n{job.description}\n{job.title}".lower()
    return any(term in location_text for term in NEW_ORLEANS_REGION_TERMS)


def _passes_location_policy(job: Job) -> bool:
    # Eligibility matrix:
    # 1) Confirmed remote labels are always eligible.
    # 2) Non-remote/hybrid roles must be explicitly in the New Orleans region.
    # 3) Unknown remote status is rejected unless New Orleans-region local context is present.
    if job.remote_label in CONFIRMED_REMOTE_LABELS and job.is_remote is True:
        return True

    if _is_new_orleans_region(job):
        return True

    return False


def _is_backend_heavy(text: str) -> bool:
    strong_backend_hits = sum(
        1
        for marker in (
            "backend",
            "api",
            "apis",
            "microservice",
            "distributed",
            "event-driven",
            "aws",
            "sqs",
            "queue",
        )
        if marker in text
    )
    return strong_backend_hits >= 2


def is_relevant_job(job: Job) -> bool:
    text = job.combined_text()
    title_text = job.title.lower()

    remote_label, remote_flag = classify_remote(job)
    job.remote_label = remote_label
    job.is_remote = remote_flag

    if not _passes_location_policy(job):
        return False

    if not any(signal in text for signal in BACKEND_SIGNALS):
        return False

    if not any(hint in title_text for hint in TITLE_REQUIRED_HINTS):
        return False

    if any(hint in title_text for hint in TITLE_REJECT_HINTS):
        return False

    if UI_REJECT_PATTERN.search(text):
        return False

    if any(term in text for term in HARD_REJECT_TERMS):
        return False

    if FULL_STACK_PATTERN.search(text) and not _is_backend_heavy(text):
        return False

    return True
