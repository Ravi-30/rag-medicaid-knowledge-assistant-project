"""Layer 6 — Data & retrieval abstractions."""

from typing import Any, Protocol


class MemberRepository(Protocol):
    async def get_member(self, member_id: str) -> dict[str, Any]: ...


class ClaimsRepository(Protocol):
    async def get_claim(self, claim_id: str) -> dict[str, Any]: ...


class InMemoryMemberRepository:
    async def get_member(self, member_id: str) -> dict[str, Any]:
        return {"member_id": member_id, "plan": "Medicaid Plus", "status": "active"}


class InMemoryClaimsRepository:
    async def get_claim(self, claim_id: str) -> dict[str, Any]:
        return {"claim_id": claim_id, "status": "in_review"}


class DataLayer:
    """Unified access to RDBMS, vector, object, cache, and search stores."""

    def __init__(
        self,
        member_repo: MemberRepository | None = None,
        claims_repo: ClaimsRepository | None = None,
    ):
        self.members = member_repo or InMemoryMemberRepository()
        self.claims = claims_repo or InMemoryClaimsRepository()

    async def get_member_context(self, member_id: str) -> dict[str, Any]:
        return await self.members.get_member(member_id)

    async def get_claim_context(self, claim_id: str) -> dict[str, Any]:
        return await self.claims.get_claim(claim_id)
