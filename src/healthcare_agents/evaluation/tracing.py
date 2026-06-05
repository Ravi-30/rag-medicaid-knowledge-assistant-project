"""Evaluation tracing hooks (LangFuse-style step tracing)."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class TraceStep:
    name: str
    input_data: dict[str, Any] = field(default_factory=dict)
    output_data: dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class StepTracer:
    """Records workflow steps for observability and evaluation pipelines."""

    def __init__(self) -> None:
        self._traces: list[TraceStep] = []

    def start_step(self, name: str, **input_data: Any) -> TraceStep:
        step = TraceStep(name=name, input_data=input_data)
        self._traces.append(step)
        return step

    def end_step(self, step: TraceStep, **output_data: Any) -> None:
        step.output_data = output_data

    def get_trace(self) -> list[dict[str, Any]]:
        return [
            {
                "name": s.name,
                "input": s.input_data,
                "output": s.output_data,
                "timestamp": s.timestamp,
            }
            for s in self._traces
        ]

    def clear(self) -> None:
        self._traces.clear()
