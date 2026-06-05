from healthcare_agents.agents.base import AgentContext, AgentResult, BaseAgent


class ClinicalSummaryAgent(BaseAgent):
    """Summarizes clinical encounters, notes, and patient history."""

    name = "clinical_summary_agent"
    description = (
        "You summarize clinical notes, encounter histories, and relevant "
        "patient data into concise, actionable summaries for care teams."
    )

    async def run(self, context: AgentContext, query: str) -> AgentResult:
        notes = context.clinical_notes
        if not notes:
            return AgentResult(
                agent_name=self.name,
                content="No clinical notes available to summarize.",
                confidence=0.0,
            )

        if self.llm_client:
            summary = await self.llm_client.chat(
                system=self._build_system_prompt(),
                user=(
                    f"Summarize the following clinical notes. "
                    f"Focus on: chief complaint, key findings, active problems, "
                    f"medications, and follow-up needs.\n\n{notes}"
                ),
            )
        else:
            summary = _rule_based_summary(notes)

        return AgentResult(
            agent_name=self.name,
            content=summary,
            confidence=0.75 if self.llm_client else 0.5,
            metadata={"note_length": len(notes)},
        )


def _rule_based_summary(notes: str) -> str:
    lines = [line.strip() for line in notes.splitlines() if line.strip()]
    preview = lines[:5]
    return (
        "Clinical Summary (rule-based)\n"
        + "\n".join(f"- {line}" for line in preview)
        + (f"\n... ({len(lines) - 5} more lines)" if len(lines) > 5 else "")
    )
