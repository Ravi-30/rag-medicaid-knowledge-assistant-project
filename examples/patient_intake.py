"""Demo: multi-agent workflow — triage then clinical summary."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from healthcare_agents.agents.base import AgentContext
from healthcare_agents.orchestrator import Orchestrator


SAMPLE_NOTES = """
Chief Complaint: Persistent cough and low-grade fever x 3 days
HPI: 45yo patient presents with dry cough, temp 100.4F, mild fatigue.
     No chest pain or shortness of breath. Non-smoker.
PMH: Hypertension (controlled on lisinopril)
Allergies: NKDA
Assessment: Likely viral URI
Plan: Supportive care, return if worsening or fever >101.5F x 48h
"""


async def main() -> None:
    orchestrator = Orchestrator(use_llm=False)

    context = AgentContext(
        patient_id="demo-002",
        symptoms=["fever", "cough"],
        clinical_notes=SAMPLE_NOTES,
    )

    results = await orchestrator.run_workflow(
        query="Patient intake for cough and fever",
        steps=["triage", "clinical_summary"],
        context=context,
    )

    print("=" * 60)
    print("PATIENT INTAKE WORKFLOW DEMO")
    print("=" * 60)

    for i, result in enumerate(results, 1):
        print(f"\n--- Step {i}: {result.agent_name} ---")
        print(result.content)


if __name__ == "__main__":
    asyncio.run(main())
