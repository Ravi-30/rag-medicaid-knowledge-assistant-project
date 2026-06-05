"""Modular reasoning loop: Think → Validate → Act → Reflect → Persist."""

from abc import abstractmethod
from typing import Any

from healthcare_agents.agents.base import AgentContext, AgentResult, BaseAgent


class ReasoningAgent(BaseAgent):
    """Base class implementing the standard agent reasoning cycle."""

    async def run(self, context: AgentContext, query: str) -> AgentResult:
        trace: list[dict[str, Any]] = []

        thought = await self._think(context, query)
        trace.append({"phase": "think", "output": thought})

        validation = await self._validate(context, query, thought)
        trace.append({"phase": "validate", "output": validation})
        if not validation.get("allowed", True):
            return AgentResult(
                agent_name=self.name,
                content=f"Validation failed: {validation.get('reason', 'unknown')}",
                confidence=0.0,
                metadata={"reasoning_trace": trace, "blocked": True},
            )

        action_result = await self._act(context, query, thought)
        trace.append({"phase": "act", "output": action_result.get("summary", "")})

        reflection = await self._reflect(context, query, action_result)
        trace.append({"phase": "reflect", "output": reflection})

        content = reflection.get("response") or action_result.get("content", "")
        return AgentResult(
            agent_name=self.name,
            content=content,
            confidence=action_result.get("confidence", 0.0),
            tool_calls=action_result.get("tool_calls", []),
            metadata={
                **action_result.get("metadata", {}),
                "reasoning_trace": trace,
                "reflection": reflection,
            },
        )

    async def _think(self, context: AgentContext, query: str) -> dict[str, Any]:
        return {
            "intent": self._infer_intent(query),
            "context_keys": list(context.metadata.keys()),
            "has_rag": bool(context.rag_context),
        }

    async def _validate(
        self, context: AgentContext, query: str, thought: dict[str, Any]
    ) -> dict[str, Any]:
        requires_member = {"eligibility", "claims", "authorization", "member_support"}
        if not context.subject_id and thought.get("intent") in requires_member:
            return {"allowed": False, "reason": "Member ID required for this request."}
        return {"allowed": True, "reason": "Validation passed."}

    @abstractmethod
    async def _act(
        self, context: AgentContext, query: str, thought: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute domain actions and return content, tool_calls, metadata."""

    async def _reflect(
        self,
        context: AgentContext,
        query: str,
        action_result: dict[str, Any],
    ) -> dict[str, Any]:
        confidence = action_result.get("confidence", 0.0)
        escalate = confidence < 0.5 or action_result.get("metadata", {}).get("risk_flags")
        return {
            "response": action_result.get("content", ""),
            "confidence_ok": confidence >= 0.5,
            "escalate": bool(escalate),
            "notes": "Review output before acting on low-confidence results." if escalate else "",
        }

    def _infer_intent(self, query: str) -> str:
        lower = query.lower()
        if "eligib" in lower or "benefit" in lower:
            return "eligibility"
        if "prior auth" in lower or "authorization" in lower:
            return "authorization"
        if "provider" in lower or "referral" in lower:
            return "provider"
        if "care plan" in lower or "care manag" in lower:
            return "care_mgmt"
        if "fraud" in lower or "duplicate" in lower or "suspicious" in lower:
            return "fraud"
        if "claim" in lower:
            return "claims"
        if "escalat" in lower or "supervisor" in lower:
            return "escalation"
        if "policy" in lower or "compliance" in lower:
            return "policy"
        if "help" in lower or "status" in lower:
            return "member_support"
        return "knowledge"
