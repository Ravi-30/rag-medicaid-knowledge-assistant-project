"""Content safety guardrails — input/output filtering beyond PHI redaction."""

import re
from dataclasses import dataclass, field

from healthcare_agents.config import settings
from healthcare_agents.safety.clinical_disclaimer import append_disclaimer
from healthcare_agents.safety.phi_guard import PHIGuard, redact_phi


@dataclass
class ContentSafetyResult:
    text: str
    blocked: bool
    warnings: list[str] = field(default_factory=list)
    labels: list[str] = field(default_factory=list)


class ContentSafetyChecker:
    """Layer 5 — content safety on inputs and outputs."""

    _INJECTION_PATTERNS = (
        "ignore all previous instructions",
        "bypass guardrails",
        "disable audit",
        "jailbreak",
        "you are now",
        "pretend you are",
    )
    _UNSAFE_MEDICAL_PATTERNS = (
        re.compile(r"\bstop taking (your )?(medication|medicine|prescription)\b", re.I),
        re.compile(r"\bno need (for|to see) (a )?(doctor|physician|emergency)\b", re.I),
        re.compile(r"\bdefinitely (have|diagnose|diagnosed with)\b", re.I),
    )
    _EMERGENCY_KEYWORDS = ("chest pain", "can't breathe", "stroke", "suicidal", "overdose")

    def __init__(self, phi_guard: PHIGuard | None = None):
        self.phi_guard = phi_guard or PHIGuard(enabled=settings.phi_redaction_enabled)

    def check_input(self, text: str) -> ContentSafetyResult:
        warnings: list[str] = []
        labels: list[str] = []
        lower = text.lower()

        if any(p in lower for p in self._INJECTION_PATTERNS):
            return ContentSafetyResult(
                text=text,
                blocked=True,
                warnings=["Prompt injection pattern detected."],
                labels=["injection"],
            )

        for pattern in self._UNSAFE_MEDICAL_PATTERNS:
            if pattern.search(text):
                warnings.append("Unsafe medical guidance pattern in input.")
                labels.append("unsafe_medical_input")
                break

        redaction = redact_phi(text)
        if redaction.redactions:
            warnings.append(f"PHI detected in input ({len(redaction.redactions)} items).")
            labels.append("phi_input")

        return ContentSafetyResult(text=redaction.text, blocked=False, warnings=warnings, labels=labels)

    def check_output(self, text: str) -> ContentSafetyResult:
        warnings: list[str] = []
        labels: list[str] = []
        lower = text.lower()

        for pattern in self._UNSAFE_MEDICAL_PATTERNS:
            if pattern.search(text):
                warnings.append("Unsafe medical guidance detected in output.")
                labels.append("unsafe_medical_output")

        if any(kw in lower for kw in self._EMERGENCY_KEYWORDS):
            warnings.append("Emergency keywords present — ensure escalation guidance is included.")
            labels.append("emergency_keywords")

        sanitized = self.phi_guard.sanitize(text)
        content = append_disclaimer(sanitized, enabled=settings.clinical_disclaimer_enabled)

        if sanitized != text:
            labels.append("phi_output")

        return ContentSafetyResult(text=content, blocked=False, warnings=warnings, labels=labels)
