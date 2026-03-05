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

HARD_REJECT_TERMS = [
    "react",
    "frontend",
    "designer",
    "mobile",
    "product manager",
    "ios",
    "android",
]

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
ONSITE_OR_HYBRID_PATTERNS = [
    re.compile(r"\bon[\s-]?site\b", re.IGNORECASE),
    re.compile(r"\bin[\s-]?office\b", re.IGNORECASE),
    re.compile(r"\bhybrid\b", re.IGNORECASE),
]


def classify_remote(job: Job) -> tuple[str, bool | None]:
    remote_text = f"{job.location}\n{job.title}\n{job.description}".lower()

    if any(pattern.search(remote_text) for pattern in REMOTE_US_PATTERNS):
        return "remote-us", True
    if any(pattern.search(remote_text) for pattern in REMOTE_FRIENDLY_PATTERNS):
        return "remote-friendly", True
    if REMOTE_PATTERN.search(remote_text):
        return "remote", True
    if any(pattern.search(remote_text) for pattern in ONSITE_OR_HYBRID_PATTERNS):
        return "onsite", False
    return "unknown", None


def _is_backend_heavy(text: str) -> bool:
    strong_backend_hits = sum(
        1
        for marker in ("backend", "api", "apis", "microservice", "distributed", "event-driven", "aws", "sqs", "queue")
        if marker in text
    )
    return strong_backend_hits >= 2


def is_relevant_job(job: Job) -> bool:
    text = job.combined_text()
    title_text = job.title.lower()

    remote_label, remote_flag = classify_remote(job)
    job.remote_label = remote_label
    job.is_remote = remote_flag

    if remote_flag is False:
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
