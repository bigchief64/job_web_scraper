from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Job:
    """Normalized job record shared across sources."""

    title: str
    company: str
    location: str
    is_remote: Optional[bool]
    description: str
    url: str
    source: str
    remote_label: str = "unknown"
    score: float = field(default=0.0)

    def combined_text(self) -> str:
        return f"{self.title}\n{self.description}".lower()
