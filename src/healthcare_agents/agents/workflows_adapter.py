"""Adapter wrapping LangGraph-style workflows as graph-orchestrator agents."""

from healthcare_agents.agents.base import AgentContext, AgentResult


class WorkflowAgentAdapter:
    """Delegates run() to a stateful workflow class."""

    def __init__(self, workflow):
        self.workflow = workflow
        self.name = workflow.name
        self.description = getattr(workflow, "description", "")

    async def run(self, context: AgentContext, query: str) -> AgentResult:
        return await self.workflow.run(context, query)
