from healthcare_agents.agents.base import AgentContext, AgentResult, BaseAgent
from healthcare_agents.tools.care_management import create_care_plan, schedule_outreach


class CareMgmtAgent(BaseAgent):
    """Manages care plans and member outreach workflows."""

    name = "care_mgmt_agent"
    description = (
        "You create care management plans, schedule member outreach, "
        "and coordinate ongoing care for high-risk populations."
    )

    async def run(self, context: AgentContext, query: str) -> AgentResult:
        member_id = context.subject_id or "member-unknown"
        conditions = context.metadata.get("conditions", ["chronic_condition"])
        goals = context.metadata.get("goals", ["improve adherence", "reduce ED visits"])

        care_plan = await create_care_plan(member_id, conditions, goals)
        outreach = await schedule_outreach(member_id, reason="care_plan_initiation")

        content = (
            f"Care Management\n"
            f"Care Plan ID: {care_plan['care_plan_id']}\n"
            f"Conditions: {', '.join(care_plan['conditions'])}\n"
            f"Goals: {', '.join(care_plan['goals'])}\n"
            f"Outreach ID: {outreach['outreach_id']}\n"
            f"Outreach Status: {outreach['status']}"
        )
        return AgentResult(
            agent_name=self.name,
            content=content,
            confidence=0.86,
            tool_calls=[
                {"tool": "create_care_plan", "result": care_plan},
                {"tool": "schedule_outreach", "result": outreach},
            ],
            metadata={"care_plan_id": care_plan["care_plan_id"]},
        )
