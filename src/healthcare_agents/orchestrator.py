import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from healthcare_agents.agents.base import AgentContext, AgentResult, BaseAgent
from healthcare_agents.agents.clinical_summary_agent import ClinicalSummaryAgent
from healthcare_agents.agents.research_agent import ResearchAgent
from healthcare_agents.agents.triage_agent import TriageAgent
from healthcare_agents.config import settings
from healthcare_agents.llm import LLMClient
from healthcare_agents.safety.clinical_disclaimer import append_disclaimer
from healthcare_agents.safety.phi_guard import PHIGuard

logger = logging.getLogger(__name__)

AgentType = Literal["triage", "clinical_summary", "research", "auto"]


class Orchestrator:
    """Coordinates multi-agent healthcare workflows with safety guardrails."""

    def __init__(self, use_llm: bool = False):
        llm = LLMClient() if use_llm and settings.openai_api_key else None
        self.agents: dict[str, BaseAgent] = {
            "triage": TriageAgent(llm),
            "clinical_summary": ClinicalSummaryAgent(llm),
            "research": ResearchAgent(llm),
        }
        self.phi_guard = PHIGuard(enabled=settings.phi_redaction_enabled)

    async def run(
        self,
        query: str,
        agent: AgentType = "auto",
        context: AgentContext | None = None,
    ) -> AgentResult:
        ctx = context or AgentContext()
        selected = self._select_agent(query, agent)

        logger.info("Running agent=%s", selected)
        self._audit_log(selected, query)

        result = await self.agents[selected].run(ctx, query)
        result.content = append_disclaimer(
            result.content, enabled=settings.clinical_disclaimer_enabled
        )
        return result

    async def run_workflow(
        self,
        query: str,
        steps: list[AgentType],
        context: AgentContext | None = None,
    ) -> list[AgentResult]:
        ctx = context or AgentContext()
        results: list[AgentResult] = []

        for step in steps:
            if step == "auto":
                step = self._select_agent(query, "auto")
            result = await self.agents[step].run(ctx, query)
            result.content = append_disclaimer(
                result.content, enabled=settings.clinical_disclaimer_enabled
            )
            results.append(result)

            if step == "triage" and "care_level" in result.metadata:
                ctx.metadata["care_level"] = result.metadata["care_level"]

        return results

    def _select_agent(self, query: str, agent: AgentType) -> str:
        if agent != "auto":
            return agent

        lower = query.lower()
        if any(kw in lower for kw in ("summarize", "summary", "notes", "encounter")):
            return "clinical_summary"
        if any(kw in lower for kw in ("research", "study", "drug", "interaction", "literature")):
            return "research"
        return "triage"

    def _audit_log(self, agent: str, query: str) -> None:
        log_path = Path(settings.audit_log_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent": agent,
            "query": self.phi_guard.sanitize_for_log(query),
        }
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
