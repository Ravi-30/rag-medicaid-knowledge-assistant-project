"""CLI — send prompts to the orchestrator (auto-routes agents + MCP tools)."""

import argparse
import asyncio
import sys

from healthcare_agents.agents.base import AgentContext
from healthcare_agents.experience.chat import ChatInterface


async def run_prompt(
    prompt: str,
    *,
    member_id: str | None = None,
    role: str = "provider",
    claim_id: str | None = None,
    chat: ChatInterface | None = None,
    session=None,
) -> None:
    chat = chat or ChatInterface()
    session = session or chat.create_session(member_id=member_id, role=role)

    metadata: dict = {}
    if claim_id:
        metadata["claim_id"] = claim_id

    ctx = AgentContext(member_id=member_id, role=role, metadata=metadata)
    result = await chat.send_message(session, prompt, context=ctx)

    print(f"\nOrchestrator: {result.metadata.get('orchestrated_by', 'graph_orchestrator')}")
    print(f"Primary agent: {result.agent_name}")
    print(f"Agents invoked: {result.metadata.get('agents_invoked', [])}")
    print(f"MCP tools used: {result.metadata.get('mcp_tools_used', [])}")
    print(f"Confidence: {result.confidence:.0%}")
    print("\n--- Response ---\n")
    print(result.content)

    if result.metadata.get("chain_results"):
        print("\n--- Agent chain ---")
        for step in result.metadata["chain_results"]:
            agent = step.get("agent")
            name = step.get("agent_name")
            conf = step.get("confidence", 0)
            print(f"  - {agent}: {name} ({conf:.0%})")


async def interactive_loop(
    *,
    member_id: str | None = None,
    role: str = "provider",
    claim_id: str | None = None,
) -> None:
    chat = ChatInterface()
    session = chat.create_session(member_id=member_id, role=role)

    print("Classroom Healthcare Medicaid Customer Service Agentic AI — Chat CLI")
    print(f"  member_id: {member_id or '(none)'}  role: {role}")
    print("  Type your prompt and press Enter. Commands: exit, quit")
    print("-" * 50)

    while True:
        try:
            prompt = await asyncio.to_thread(input, "\nYou: ")
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            break

        prompt = prompt.strip()
        if not prompt:
            continue
        if prompt.lower() in ("exit", "quit", "q"):
            print("Bye.")
            break

        await run_prompt(
            prompt,
            member_id=member_id,
            role=role,
            claim_id=claim_id,
            chat=chat,
            session=session,
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="healthcare-chat",
        description="Send prompts to the healthcare orchestrator (auto-routes agents + MCP).",
    )
    parser.add_argument(
        "prompt",
        nargs="?",
        help="Your request (omit for interactive mode with -i)",
    )
    parser.add_argument(
        "-i",
        "--interactive",
        action="store_true",
        help="Interactive prompt loop",
    )
    parser.add_argument("--member-id", default="member-001", help="Member ID")
    parser.add_argument(
        "--role",
        default="provider",
        choices=["member", "provider", "ops_analyst", "admin"],
        help="Caller role for RBAC",
    )
    parser.add_argument("--claim-id", help="Claim ID for claims lookup/adjustment")
    args = parser.parse_args()

    if args.interactive or not args.prompt:
        if not args.interactive and not sys.stdin.isatty():
            prompt = sys.stdin.read().strip()
            if prompt:
                asyncio.run(
                    run_prompt(
                        prompt,
                        member_id=args.member_id,
                        role=args.role,
                        claim_id=args.claim_id,
                    )
                )
                return
        asyncio.run(
            interactive_loop(
                member_id=args.member_id,
                role=args.role,
                claim_id=args.claim_id,
            )
        )
        return

    asyncio.run(
        run_prompt(
            args.prompt,
            member_id=args.member_id,
            role=args.role,
            claim_id=args.claim_id,
        )
    )


if __name__ == "__main__":
    main()
