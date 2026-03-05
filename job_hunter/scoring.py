from __future__ import annotations

import re

from .models import Job

POSITIVE_WEIGHTS = {
    "node": 5,
    "typescript": 5,
    "go": 5,
    "apis": 4,
    "distributed": 4,
    "aws": 3,
    "microservices": 3,
    "event-driven": 3,
}

NEGATIVE_WEIGHTS = {
    "react": -10,
    "frontend": -8,
    "ui": -8,
}

API_PATTERN = re.compile(r"\bapi(s)?\b", re.IGNORECASE)
GO_PATTERN = re.compile(r"\b(go|golang)\b", re.IGNORECASE)
UI_PATTERN = re.compile(r"\bui\b", re.IGNORECASE)


def _contains_token(text: str, token: str) -> bool:
    if token == "apis":
        return bool(API_PATTERN.search(text))
    if token == "go":
        return bool(GO_PATTERN.search(text))
    if token == "ui":
        return bool(UI_PATTERN.search(text))
    return token in text


def score_job(job: Job) -> float:
    text = job.combined_text()
    score = 0.0

    for token, weight in POSITIVE_WEIGHTS.items():
        if _contains_token(text, token):
            score += weight

    for token, weight in NEGATIVE_WEIGHTS.items():
        if _contains_token(text, token):
            score += weight

    job.score = score
    return score
