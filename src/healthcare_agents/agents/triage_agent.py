from healthcare_agents.agents.base import AgentContext, AgentResult, BaseAgent
from healthcare_agents.tools.medical_knowledge import check_symptoms


class TriageAgent(BaseAgent):
    """Assesses symptom severity and recommends an appropriate care level."""

    name = "triage_agent"
    description = (
        "You assess patient symptoms and recommend care urgency "
        "(self-care, primary care, urgent care, or emergency)."
    )

    async def run(self, context: AgentContext, query: str) -> AgentResult:
        symptoms = context.symptoms or _extract_symptoms(query)
        assessment = check_symptoms(symptoms)

        care_level = assessment["recommended_care_level"]
        urgency_score = assessment["urgency_score"]

        content = (
            f"Triage Assessment\n"
            f"Symptoms: {', '.join(symptoms) if symptoms else 'none specified'}\n"
            f"Urgency Score: {urgency_score}/10\n"
            f"Recommended Care Level: {care_level}\n"
            f"Rationale: {assessment['rationale']}"
        )

        if self.llm_client:
            content = await self._enrich_with_llm(context, query, content)

        return AgentResult(
            agent_name=self.name,
            content=content,
            confidence=assessment["confidence"],
            metadata={"care_level": care_level, "urgency_score": urgency_score},
        )

    async def _enrich_with_llm(self, context: AgentContext, query: str, base: str) -> str:
        response = await self.llm_client.chat(
            system=self._build_system_prompt(),
            user=f"Patient query: {query}\n\nBase assessment:\n{base}\n\nProvide a clear, empathetic triage summary.",
        )
        return response

    def _build_system_prompt(self) -> str:
        return super()._build_system_prompt() + (
            " Use evidence-based triage protocols. Flag red-flag symptoms immediately."
        )


def _extract_symptoms(text: str) -> list[str]:
    keywords = ["fever", "cough", "chest pain", "headache", "nausea", "shortness of breath"]
    lower = text.lower()
    return [kw for kw in keywords if kw in lower]
