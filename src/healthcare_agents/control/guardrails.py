"""Input/output guardrails — delegates to layered content safety checks."""

from dataclasses import dataclass

from healthcare_agents.control.content_safety import ContentSafetyChecker


@dataclass
class GuardrailResult:
    text: str
    blocked: bool
    warnings: list[str]


class Guardrails:
    """Unified input/output safety checks applied before and after agent execution."""

    def __init__(self, content_safety: ContentSafetyChecker | None = None):
        self.content_safety = content_safety or ContentSafetyChecker()

    def check_input(self, text: str) -> GuardrailResult:
        result = self.content_safety.check_input(text)
        return GuardrailResult(text=result.text, blocked=result.blocked, warnings=result.warnings)

    def check_output(self, text: str) -> GuardrailResult:
        result = self.content_safety.check_output(text)
        return GuardrailResult(text=result.text, blocked=result.blocked, warnings=result.warnings)
