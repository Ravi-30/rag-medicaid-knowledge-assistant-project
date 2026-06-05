import argparse
import asyncio
import logging

from healthcare_agents.agents.base import AgentContext
from healthcare_agents.config import settings
from healthcare_agents.orchestrator import Orchestrator


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Classroom Healthcare Medicaid Customer Service Agentic AI CLI"
    )
    parser.add_argument("query", help="Patient or clinical query")
    parser.add_argument(
        "--agent",
        choices=["triage", "clinical_summary", "research", "auto"],
        default="auto",
    )
    parser.add_argument("--use-llm", action="store_true", help="Enable LLM enrichment")
    parser.add_argument("--symptoms", nargs="*", help="List of symptoms")
    parser.add_argument("--notes", default="", help="Clinical notes for summary agent")
    args = parser.parse_args()

    logging.basicConfig(level=settings.log_level)

    context = AgentContext(
        symptoms=args.symptoms or [],
        clinical_notes=args.notes,
    )

    orchestrator = Orchestrator(use_llm=args.use_llm)
    result = asyncio.run(orchestrator.run(args.query, agent=args.agent, context=context))

    print(f"\n[{result.agent_name}] (confidence: {result.confidence:.0%})")
    print(result.content)


if __name__ == "__main__":
    main()
