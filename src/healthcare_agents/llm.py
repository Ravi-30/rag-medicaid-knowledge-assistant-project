"""LLM client abstraction — supports OpenAI with optional fallback."""

from healthcare_agents.config import settings


class LLMClient:
    def __init__(self, provider: str | None = None, model: str | None = None):
        self.provider = provider or settings.llm_provider
        self.model = model or settings.llm_model
        self._client = None

    def _get_openai_client(self):
        if self._client is None:
            try:
                from openai import AsyncOpenAI
            except ImportError as e:
                raise ImportError("Install openai: pip install healthcare-agents[openai]") from e
            self._client = AsyncOpenAI(api_key=settings.openai_api_key)
        return self._client

    async def chat(self, system: str, user: str) -> str:
        if self.provider == "openai":
            client = self._get_openai_client()
            response = await client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
            return response.choices[0].message.content or ""
        raise ValueError(f"Unsupported LLM provider: {self.provider}")
