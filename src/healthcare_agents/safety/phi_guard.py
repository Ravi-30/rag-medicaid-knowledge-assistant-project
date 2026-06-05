"""PHI detection and redaction before logging or external transmission."""

import re
from dataclasses import dataclass

PHI_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("SSN", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("PHONE", re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b")),
    ("EMAIL", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")),
    ("MRN", re.compile(r"\bMRN[:\s#]*\d+\b", re.IGNORECASE)),
    ("DOB", re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b")),
]


@dataclass
class RedactionResult:
    text: str
    redactions: list[str]


def redact_phi(text: str) -> RedactionResult:
    redactions: list[str] = []
    result = text

    for label, pattern in PHI_PATTERNS:
        matches = pattern.findall(result)
        if matches:
            redactions.extend(f"{label}: {m}" for m in matches)
            result = pattern.sub(f"[REDACTED_{label}]", result)

    return RedactionResult(text=result, redactions=redactions)


class PHIGuard:
    """Wraps text processing to enforce PHI redaction policy."""

    def __init__(self, enabled: bool = True):
        self.enabled = enabled

    def sanitize(self, text: str) -> str:
        if not self.enabled:
            return text
        return redact_phi(text).text

    def sanitize_for_log(self, text: str) -> str:
        return self.sanitize(text)
