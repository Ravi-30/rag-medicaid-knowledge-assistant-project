"""Layer 2 — Application API auth (OAuth2/OIDC stub)."""

from dataclasses import dataclass


@dataclass
class AuthContext:
    subject: str
    role: str
    scopes: frozenset[str]


class AuthService:
    """AuthN/AuthZ stub — replace with OAuth2/OIDC + IAM in production."""

    _API_KEYS: dict[str, AuthContext] = {
        "member-demo-key": AuthContext("member-001", "member", frozenset({"read", "write"})),
        "provider-demo-key": AuthContext("provider-101", "provider", frozenset({"read", "write"})),
        "ops-demo-key": AuthContext("ops-analyst", "ops_analyst", frozenset({"read", "write", "admin"})),
    }

    def authenticate(self, api_key: str | None) -> AuthContext | None:
        if not api_key:
            return None
        return self._API_KEYS.get(api_key)

    def authorize(self, auth: AuthContext, required_scope: str = "read") -> bool:
        return required_scope in auth.scopes or "admin" in auth.scopes
