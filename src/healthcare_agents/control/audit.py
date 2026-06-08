"""Audit logging for PHI access and agent actions (Layer 6)."""

import json
from datetime import datetime, timezone
UTC = timezone.utc
from pathlib import Path
from typing import Any

from healthcare_agents.config import settings
from healthcare_agents.safety.phi_guard import PHIGuard


class AuditLogger:
    def __init__(self, phi_guard: PHIGuard | None = None):
        self.phi_guard = phi_guard or PHIGuard(enabled=settings.phi_redaction_enabled)

    def log(self, event: str, **fields: Any) -> None:
        log_path = Path(settings.audit_log_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        sanitized = {
            key: self.phi_guard.sanitize_for_log(str(value)) if isinstance(value, str) else value
            for key, value in fields.items()
        }
        entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "event": event,
            **sanitized,
        }
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
