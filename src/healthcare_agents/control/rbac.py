"""Role-based access control for agent and tool execution (Layer 6)."""

from dataclasses import dataclass


@dataclass
class Role:
    name: str
    permissions: frozenset[str]


class RBAC:
    """Simple role-based permission checks for operational workflows."""

    _ROLES: dict[str, Role] = {
        "member": Role(
            "member",
            frozenset(
                {
                    "read_own_eligibility",
                    "submit_inquiry",
                    "read_policy",
                }
            ),
        ),
        "provider": Role(
            "provider",
            frozenset(
                {
                    "verify_eligibility",
                    "submit_prior_auth",
                    "submit_claim",
                    "lookup_provider",
                }
            ),
        ),
        "care_manager": Role(
            "care_manager",
            frozenset(
                {
                    "verify_eligibility",
                    "manage_care_plan",
                    "lookup_provider",
                    "read_policy",
                    "submit_inquiry",
                }
            ),
        ),
        "ops_analyst": Role(
            "ops_analyst",
            frozenset(
                {
                    "verify_eligibility",
                    "submit_prior_auth",
                    "submit_claim",
                    "manage_care_plan",
                    "lookup_provider",
                    "read_policy",
                    "investigate_fraud",
                    "submit_inquiry",
                    "process_refund",
                }
            ),
        ),
        "admin": Role("admin", frozenset({"*"})),
    }

    def can(self, role: str, permission: str) -> bool:
        role_obj = self._ROLES.get(role)
        if not role_obj:
            return False
        return "*" in role_obj.permissions or permission in role_obj.permissions
