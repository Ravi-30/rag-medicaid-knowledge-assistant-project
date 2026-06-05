"""Session and persistent workflow memory (Layer 4)."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


@dataclass
class MemoryEntry:
    role: str
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CaseRecord:
    case_id: str
    member_id: str | None
    status: str
    workflow_type: str
    history: list[MemoryEntry] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class SessionMemory:
    """Short-term conversation state for an active session."""

    def __init__(self) -> None:
        self._sessions: dict[str, list[MemoryEntry]] = {}

    def append(self, session_id: str, role: str, content: str, **metadata: Any) -> None:
        self._sessions.setdefault(session_id, []).append(
            MemoryEntry(role=role, content=content, metadata=metadata)
        )

    def get_history(self, session_id: str, limit: int = 20) -> list[MemoryEntry]:
        return self._sessions.get(session_id, [])[-limit:]

    def clear(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)


class PersistentMemory:
    """Long-term workflow state, cases, and checkpoints."""

    def __init__(self) -> None:
        self._cases: dict[str, CaseRecord] = {}

    def create_case(
        self,
        member_id: str | None,
        workflow_type: str,
        metadata: dict[str, Any] | None = None,
    ) -> CaseRecord:
        case_id = f"case-{uuid4().hex[:12]}"
        record = CaseRecord(
            case_id=case_id,
            member_id=member_id,
            status="open",
            workflow_type=workflow_type,
            metadata=metadata or {},
        )
        self._cases[case_id] = record
        return record

    def get_case(self, case_id: str) -> CaseRecord | None:
        return self._cases.get(case_id)

    def update_case(
        self,
        case_id: str,
        *,
        status: str | None = None,
        entry: MemoryEntry | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> CaseRecord | None:
        record = self._cases.get(case_id)
        if not record:
            return None

        if status:
            record.status = status
        if entry:
            record.history.append(entry)
        if metadata:
            record.metadata.update(metadata)
        record.updated_at = datetime.now(UTC).isoformat()
        return record

    def save_checkpoint(self, case_id: str, checkpoint: dict[str, Any]) -> None:
        record = self._cases.get(case_id)
        if record:
            record.metadata["checkpoint"] = checkpoint
            record.updated_at = datetime.now(UTC).isoformat()
