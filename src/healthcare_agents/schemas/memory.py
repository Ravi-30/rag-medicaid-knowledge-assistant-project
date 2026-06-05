"""Structured memory & context agent outputs."""

from pydantic import BaseModel, Field


class MemoryArtifact(BaseModel):
    summarized_context: str
    memory_delta: dict[str, object] = Field(default_factory=dict)
    retrieval_index: list[str] = Field(default_factory=list)
    conflicts_detected: list[str] = Field(default_factory=list)
    pruned_tokens: int = 0
