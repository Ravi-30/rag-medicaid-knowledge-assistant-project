from typing import Any

from healthcare_agents.agents.base import AgentContext
from healthcare_agents.agents.reasoning import ReasoningAgent


class FraudAgent(ReasoningAgent):
    """Payment integrity and fraud investigation agent."""

    name = "fraud_agent"
    description = (
        "You investigate suspicious claims activity, duplicate submissions, "
        "and payment integrity violations."
    )

    _FRAUD_SIGNALS = ("duplicate", "suspicious", "fraud", "overbilling", "upcoding")

    async def _validate(
        self, context: AgentContext, query: str, thought: dict[str, Any]
    ) -> dict[str, Any]:
        return {"allowed": True, "reason": "Fraud review uses claim/case context."}

    async def _act(
        self, context: AgentContext, query: str, thought: dict[str, Any]
    ) -> dict[str, Any]:
        lower = query.lower()
        signals = [s for s in self._FRAUD_SIGNALS if s in lower]
        claim_id = context.metadata.get("claim_id", "unknown")
        risk_level = "high" if len(signals) >= 2 else "medium" if signals else "low"

        content = (
            f"Payment Integrity & Fraud Review\n"
            f"Claim/Case: {claim_id}\n"
            f"Risk Level: {risk_level}\n"
            f"Signals: {', '.join(signals) if signals else 'routine review'}"
        )
        if risk_level in ("high", "medium"):
            content += "\nAction: Case flagged for SIU review."

        return {
            "content": content,
            "confidence": 0.78,
            "metadata": {"risk_level": risk_level, "signals": signals},
        }
