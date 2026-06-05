"""Layered guardrail strategy — unified safety across the orchestration pipeline."""

from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel

from healthcare_agents.control.content_safety import ContentSafetyChecker
from healthcare_agents.control.guardrails import GuardrailResult, Guardrails
from healthcare_agents.control.hitl import HumanInTheLoop
from healthcare_agents.control.output_constraints import StructuredOutputValidator
from healthcare_agents.control.policy_engine import PolicyEngine
from healthcare_agents.control.prompt_guidance import PromptGuidance
from healthcare_agents.tools.mcp.governance import GovernanceDecision

_TOOL_ACTION_MAP: dict[str, str] = {
    "get_profile": "verify_eligibility",
    "verify_identity": "verify_eligibility",
    "process_refund": "process_refund",
    "check_refund_eligibility": "process_refund",
    "submit_prior_auth": "submit_prior_auth",
    "book_appointment": "submit_inquiry",
    "get_case_status": "submit_claim",
}

_SENSITIVE_TOOLS = frozenset({"process_refund", "cancel_order"})


@dataclass
class GuardrailLayerResult:
    layer: str
    passed: bool
    blocked: bool = False
    requires_hitl: bool = False
    warnings: list[str] = field(default_factory=list)
    reason: str = ""


@dataclass
class GuardrailPipelineResult:
    allowed: bool
    blocked: bool = False
    requires_hitl: bool = False
    sanitized_text: str = ""
    layers: list[GuardrailLayerResult] = field(default_factory=list)
    hitl_reason: str = ""

    @property
    def warnings(self) -> list[str]:
        out: list[str] = []
        for layer in self.layers:
            out.extend(layer.warnings)
        return out


class GuardrailStrategy:
    """Coordinates six guardrail layers across the agentic pipeline."""

    def __init__(
        self,
        guardrails: Guardrails | None = None,
        content_safety: ContentSafetyChecker | None = None,
        policy_engine: PolicyEngine | None = None,
        hitl: HumanInTheLoop | None = None,
        output_validator: StructuredOutputValidator | None = None,
        prompt_guidance: PromptGuidance | None = None,
    ):
        self.content_safety = content_safety or ContentSafetyChecker()
        self.guardrails = guardrails or Guardrails()
        self.policy_engine = policy_engine or PolicyEngine()
        self.hitl = hitl or HumanInTheLoop()
        self.output_validator = output_validator or StructuredOutputValidator()
        self.prompt_guidance = prompt_guidance or PromptGuidance()

    # Layer 1 — prompt-level guidance
    def apply_prompt_guidance(
        self, *, role: str, agent: str, query: str
    ) -> tuple[str, GuardrailLayerResult]:
        result = self.prompt_guidance.build(role=role, agent=agent, query=query)
        layer = GuardrailLayerResult(
            layer="prompt_guidance",
            passed=True,
            warnings=[],
            reason=result.guidance[:120],
        )
        return result.guidance, layer

    # Layer 2 — structured-output constraints
    def validate_structured_output(
        self, model: type[BaseModel], data: dict[str, Any]
    ) -> tuple[dict[str, Any] | None, GuardrailLayerResult]:
        result = self.output_validator.validate(model, data)
        layer = GuardrailLayerResult(
            layer="structured_output",
            passed=result.valid,
            blocked=not result.valid,
            warnings=result.errors,
            reason="Schema validation failed." if not result.valid else "Schema valid.",
        )
        return (result.data if result.valid else None), layer

    # Layer 3 — MCP tool governance
    def check_mcp_tool(self, tool_name: str, payload: dict[str, Any]) -> GovernanceDecision:
        action = _TOOL_ACTION_MAP.get(tool_name, tool_name)
        policy = self.policy_engine.evaluate(action, payload)
        if not policy.allowed:
            return GovernanceDecision(allowed=False, reason=policy.reason)

        if tool_name in _SENSITIVE_TOOLS:
            amount = payload.get("amount_usd", 0)
            if self.hitl.requires_review(action, {**payload, "cost_usd": amount}):
                return GovernanceDecision(
                    allowed=False,
                    reason=f"Tool '{tool_name}' requires human approval before execution.",
                )

        masked = dict(payload)
        return GovernanceDecision(allowed=True, masked_payload=masked)

    # Layer 4 — policy validation
    def validate_policy(self, action: str, payload: dict[str, Any]) -> GuardrailLayerResult:
        decision = self.policy_engine.evaluate(action, payload)
        return GuardrailLayerResult(
            layer="policy_validation",
            passed=decision.allowed,
            blocked=not decision.allowed,
            reason=decision.reason,
        )

    # Layer 5 — content safety
    def check_input(self, text: str) -> GuardrailPipelineResult:
        safety = self.content_safety.check_input(text)
        legacy = self.guardrails.check_input(text)
        blocked = safety.blocked or legacy.blocked
        layer = GuardrailLayerResult(
            layer="content_safety_input",
            passed=not blocked,
            blocked=blocked,
            warnings=safety.warnings + legacy.warnings,
            reason="Input blocked by content safety." if blocked else "",
        )
        return GuardrailPipelineResult(
            allowed=not blocked,
            blocked=blocked,
            sanitized_text=safety.text,
            layers=[layer],
        )

    def check_output(self, text: str) -> GuardrailPipelineResult:
        safety = self.content_safety.check_output(text)
        layer = GuardrailLayerResult(
            layer="content_safety_output",
            passed=True,
            warnings=safety.warnings,
        )
        return GuardrailPipelineResult(
            allowed=True,
            sanitized_text=safety.text,
            layers=[layer],
        )

    # Layer 6 — human approval for sensitive actions
    def check_human_approval(
        self,
        action: str,
        payload: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> GuardrailLayerResult:
        meta = {**(metadata or {}), **payload}
        requires = self.hitl.requires_review(action, meta)
        return GuardrailLayerResult(
            layer="human_approval",
            passed=not requires,
            requires_hitl=requires,
            reason="Sensitive action requires human approval." if requires else "",
        )

    def run_pre_execution(
        self,
        query: str,
        action: str,
        payload: dict[str, Any],
        *,
        role: str = "ops_analyst",
        agent: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> GuardrailPipelineResult:
        """Run input, prompt, policy, and HITL checks before agent/tool execution."""
        layers: list[GuardrailLayerResult] = []

        input_result = self.check_input(query)
        layers.extend(input_result.layers)
        if input_result.blocked:
            return GuardrailPipelineResult(
                allowed=False,
                blocked=True,
                sanitized_text=input_result.sanitized_text,
                layers=layers,
            )

        _, prompt_layer = self.apply_prompt_guidance(role=role, agent=agent or action, query=query)
        layers.append(prompt_layer)

        policy_layer = self.validate_policy(action, payload)
        layers.append(policy_layer)

        hitl_layer = self.check_human_approval(action, payload, metadata)
        layers.append(hitl_layer)

        blocked = policy_layer.blocked
        requires_hitl = hitl_layer.requires_hitl
        return GuardrailPipelineResult(
            allowed=not blocked and not requires_hitl,
            blocked=blocked,
            requires_hitl=requires_hitl,
            sanitized_text=input_result.sanitized_text,
            layers=layers,
            hitl_reason=hitl_layer.reason,
        )

    def run_post_execution(
        self,
        text: str,
        action: str,
        payload: dict[str, Any],
        *,
        structured_model: type[BaseModel] | None = None,
        structured_data: dict[str, Any] | None = None,
    ) -> GuardrailPipelineResult:
        """Run output safety and optional structured validation after execution."""
        layers: list[GuardrailLayerResult] = []

        output_result = self.check_output(text)
        layers.extend(output_result.layers)

        if structured_model and structured_data is not None:
            _, struct_layer = self.validate_structured_output(structured_model, structured_data)
            layers.append(struct_layer)
            if struct_layer.blocked:
                return GuardrailPipelineResult(
                    allowed=False,
                    blocked=True,
                    sanitized_text=output_result.sanitized_text,
                    layers=layers,
                )

        policy_layer = self.validate_policy(action, payload)
        layers.append(policy_layer)

        return GuardrailPipelineResult(
            allowed=policy_layer.passed,
            blocked=not policy_layer.passed,
            sanitized_text=output_result.sanitized_text,
            layers=layers,
        )

    def to_guardrail_result(self, pipeline: GuardrailPipelineResult) -> GuardrailResult:
        """Backward-compatible adapter for legacy Guardrails callers."""
        return GuardrailResult(
            text=pipeline.sanitized_text,
            blocked=pipeline.blocked,
            warnings=pipeline.warnings,
        )
