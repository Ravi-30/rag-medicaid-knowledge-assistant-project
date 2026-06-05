"""Structured-output guardrails — Pydantic validation before consumption."""

from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, ValidationError


@dataclass
class OutputConstraintResult:
    valid: bool
    data: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


class StructuredOutputValidator:
    """Layer 2 — enforce schema contracts on agent and tool outputs."""

    def validate(self, model: type[BaseModel], data: dict[str, Any]) -> OutputConstraintResult:
        try:
            parsed = model.model_validate(data)
            return OutputConstraintResult(valid=True, data=parsed.model_dump())
        except ValidationError as exc:
            return OutputConstraintResult(
                valid=False,
                errors=[e["msg"] for e in exc.errors()],
            )

    def validate_required_fields(
        self, data: dict[str, Any], required: list[str]
    ) -> OutputConstraintResult:
        missing = [f for f in required if not data.get(f)]
        if missing:
            return OutputConstraintResult(
                valid=False,
                errors=[f"Missing required fields: {', '.join(missing)}"],
            )
        return OutputConstraintResult(valid=True, data=data)
