"""FHIR R4 client for healthcare resource access."""

import httpx

from healthcare_agents.config import settings


class FHIRClient:
    def __init__(self, base_url: str | None = None):
        self.base_url = (base_url or settings.fhir_base_url).rstrip("/")

    async def get_patient(self, patient_id: str) -> dict | None:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/Patient/{patient_id}")
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()

    async def search_observations(self, patient_id: str, code: str | None = None) -> list[dict]:
        params: dict[str, str] = {"patient": patient_id}
        if code:
            params["code"] = code

        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/Observation", params=params)
            response.raise_for_status()
            bundle = response.json()
            return bundle.get("entry", [])

    async def get_conditions(self, patient_id: str) -> list[dict]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/Condition", params={"patient": patient_id}
            )
            response.raise_for_status()
            bundle = response.json()
            return bundle.get("entry", [])
