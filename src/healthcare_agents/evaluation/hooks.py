"""Runtime evaluation hooks — structured logging at key orchestration stages."""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
UTC = timezone.utc
try:
    from enum import StrEnum
except ImportError:
    from enum import Enum
    class StrEnum(str, Enum):
        pass
from typing import Any
from uuid import uuid4


class EvaluationEventType(StrEnum):
    EVIDENCE_RETRIEVED = "evidence_retrieved"
    TOOLS_CHOSEN = "tools_chosen"
    POLICY_OUTCOME = "policy_outcome"
    EXECUTION_RESULT = "execution_result"
    REFLECTION_DECISION = "reflection_decision"
    ESCALATION_EVENT = "escalation_event"


@dataclass
class EvaluationEvent:
    event_type: EvaluationEventType
    stage: str
    run_id: str
    payload: dict[str, Any] = field(default_factory=dict)
    case_id: str | None = None
    member_id: str | None = None
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class RuntimeEvaluationHooks:
    """Logs evaluation events at key runtime stages for observability and offline eval."""

    def __init__(
        self,
        audit_callback: Callable[[str, dict[str, Any]], None] | None = None,
        event_callback: Callable[[EvaluationEvent], None] | None = None,
    ):
        self.audit_callback = audit_callback
        self.event_callback = event_callback
        self._events: list[EvaluationEvent] = []
        self._run_id: str | None = None

    def begin_run(
        self,
        *,
        case_id: str | None = None,
        member_id: str | None = None,
        query: str = "",
    ) -> str:
        self.clear()
        self._run_id = f"eval-{uuid4().hex[:12]}"
        self._emit(
            EvaluationEventType.EXECUTION_RESULT,
            stage="run_start",
            payload={"query": query[:200], "status": "started"},
            case_id=case_id,
            member_id=member_id,
        )
        return self._run_id

    @property
    def run_id(self) -> str | None:
        return self._run_id

    def log_evidence_retrieved(
        self,
        *,
        snippets: list[str],
        sources: list[str],
        token_estimate: int = 0,
        case_id: str | None = None,
        member_id: str | None = None,
        **extra: Any,
    ) -> None:
        self._emit(
            EvaluationEventType.EVIDENCE_RETRIEVED,
            stage="context_enrichment",
            payload={
                "snippet_count": len(snippets),
                "sources": sources,
                "token_estimate": token_estimate,
                "sample_snippets": [s[:120] for s in snippets[:3]],
                **extra,
            },
            case_id=case_id,
            member_id=member_id,
        )

    def log_tools_chosen(
        self,
        *,
        tools: list[str],
        agent: str,
        case_id: str | None = None,
        member_id: str | None = None,
        **extra: Any,
    ) -> None:
        self._emit(
            EvaluationEventType.TOOLS_CHOSEN,
            stage="tool_selection",
            payload={"tools": tools, "agent": agent, **extra},
            case_id=case_id,
            member_id=member_id,
        )

    def log_policy_outcome(
        self,
        *,
        action: str,
        allowed: bool,
        reason: str = "",
        requires_hitl: bool = False,
        rule_id: str | None = None,
        case_id: str | None = None,
        member_id: str | None = None,
        **extra: Any,
    ) -> None:
        self._emit(
            EvaluationEventType.POLICY_OUTCOME,
            stage="governed_decision",
            payload={
                "action": action,
                "allowed": allowed,
                "reason": reason,
                "requires_hitl": requires_hitl,
                "rule_id": rule_id,
                **extra,
            },
            case_id=case_id,
            member_id=member_id,
        )

    def log_execution_result(
        self,
        *,
        agent: str,
        success: bool,
        confidence: float = 0.0,
        summary: str = "",
        tool_results: dict[str, Any] | None = None,
        case_id: str | None = None,
        member_id: str | None = None,
        **extra: Any,
    ) -> None:
        self._emit(
            EvaluationEventType.EXECUTION_RESULT,
            stage="agent_execution",
            payload={
                "agent": agent,
                "success": success,
                "confidence": confidence,
                "summary": summary[:300],
                "tool_results": tool_results or {},
                **extra,
            },
            case_id=case_id,
            member_id=member_id,
        )

    def log_reflection_decision(
        self,
        *,
        confidence: float,
        escalate: bool,
        resolved: bool = False,
        notes: str = "",
        case_id: str | None = None,
        member_id: str | None = None,
        **extra: Any,
    ) -> None:
        self._emit(
            EvaluationEventType.REFLECTION_DECISION,
            stage="reflection",
            payload={
                "confidence": confidence,
                "escalate": escalate,
                "resolved": resolved,
                "notes": notes,
                **extra,
            },
            case_id=case_id,
            member_id=member_id,
        )

    def log_escalation_event(
        self,
        *,
        escalation_id: str,
        reason: str,
        priority: str = "normal",
        case_id: str | None = None,
        member_id: str | None = None,
        **extra: Any,
    ) -> None:
        self._emit(
            EvaluationEventType.ESCALATION_EVENT,
            stage="escalation",
            payload={
                "escalation_id": escalation_id,
                "reason": reason,
                "priority": priority,
                **extra,
            },
            case_id=case_id,
            member_id=member_id,
        )

    def get_events(self) -> list[dict[str, Any]]:
        return [
            {
                "event_type": e.event_type,
                "stage": e.stage,
                "run_id": e.run_id,
                "case_id": e.case_id,
                "member_id": e.member_id,
                "timestamp": e.timestamp,
                "payload": e.payload,
            }
            for e in self._events
        ]

    def get_summary(self) -> dict[str, Any]:
        by_type: dict[str, int] = {}
        for event in self._events:
            by_type[event.event_type] = by_type.get(event.event_type, 0) + 1
        return {
            "run_id": self._run_id,
            "total_events": len(self._events),
            "by_type": by_type,
        }

    def clear(self) -> None:
        self._events.clear()
        self._run_id = None

    def _emit(
        self,
        event_type: EvaluationEventType,
        stage: str,
        payload: dict[str, Any],
        case_id: str | None = None,
        member_id: str | None = None,
    ) -> None:
        run_id = self._run_id or f"eval-{uuid4().hex[:12]}"
        event = EvaluationEvent(
            event_type=event_type,
            stage=stage,
            run_id=run_id,
            payload=payload,
            case_id=case_id,
            member_id=member_id,
        )
        self._events.append(event)

        if self.audit_callback:
            self.audit_callback(
                f"eval_{event_type}",
                {
                    "run_id": run_id,
                    "stage": stage,
                    "case_id": case_id,
                    "member_id": member_id,
                    **payload,
                },
            )
        if self.event_callback:
            self.event_callback(event)
