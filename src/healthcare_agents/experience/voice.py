"""Voice interface stub (IVR / Voice AI) — Layer 1."""

from healthcare_agents.experience.chat import ChatInterface, ChatSession


class VoiceInterface:
    """Speech-to-text / text-to-speech adapter over ChatInterface."""

    def __init__(self, chat: ChatInterface | None = None):
        self.chat = chat or ChatInterface()

    def create_session(self, member_id: str | None = None) -> ChatSession:
        return self.chat.create_session(member_id=member_id, role="member")

    async def handle_transcript(self, session: ChatSession, transcript: str):
        """Process voice transcript as text query."""
        return await self.chat.send_message(session, transcript)
