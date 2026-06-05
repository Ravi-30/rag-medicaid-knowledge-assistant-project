"""Domain agent registry — maps system design agent names to implementation."""

# System design name → implementation reference
DOMAIN_AGENTS: dict[str, dict[str, str]] = {
    "triage_agent": {
        "module": "agents/platform/triage_routing_agent.py",
        "class": "TriageRoutingAgent",
        "purpose": "Intake & Classification",
    },
    "claims_processing_agent": {
        "module": "agents/operational/claims_agent.py",
        "class": "ClaimsAgent",
        "purpose": "Claims & Adjustments",
    },
    "eligibility_agent": {
        "module": "agents/operational/eligibility_agent.py",
        "class": "EligibilityAgent",
        "purpose": "Eligibility & Benefits",
    },
    "prior_auth_agent": {
        "module": "agents/operational/authorization_agent.py",
        "class": "AuthorizationAgent",
        "purpose": "Authorization Workflows",
    },
    "appointment_agent": {
        "module": "workflows/service_appointment.py",
        "class": "ServiceAppointmentWorkflow",
        "purpose": "Scheduling & Reminders",
    },
    "care_coordination_agent": {
        "module": "agents/operational/care_mgmt_agent.py",
        "class": "CareMgmtAgent",
        "purpose": "Care Plans & Follow-ups",
    },
    "policy_compliance_agent": {
        "module": "agents/operational/policy_compliance_agent.py",
        "class": "PolicyComplianceAgent",
        "purpose": "Rules & Guidelines",
    },
    "provider_coordination_agent": {
        "module": "agents/operational/provider_agent.py",
        "class": "ProviderAgent",
        "purpose": "Provider Network & Referrals",
    },
}


def list_domain_agents() -> list[dict[str, str]]:
    return [{"name": k, **v} for k, v in DOMAIN_AGENTS.items()]
