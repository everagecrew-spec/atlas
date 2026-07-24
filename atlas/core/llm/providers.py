from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass

from atlas.config.models import LLMConfig
from atlas.core.dialog.memory import ConversationMemory


@dataclass(slots=True)
class ChatResponse:
    text: str


class ChatModel:
    def generate_reply(self, message: str, memory: ConversationMemory) -> ChatResponse:
        raise NotImplementedError


class OllamaChatModel(ChatModel):
    def __init__(self, config: LLMConfig) -> None:
        self._config = config

    def generate_reply(self, message: str, memory: ConversationMemory) -> ChatResponse:
        payload = {
            "model": self._config.model,
            "stream": False,
            "messages": memory.as_messages(self._config.system_prompt),
        }
        request = urllib.request.Request(
            url=f"{self._config.host.rstrip('/')}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self._config.timeout_s) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise RuntimeError(
                "Unable to reach local Ollama API. Start Ollama and pull the configured model, or use chat fallback."
            ) from exc
        text = body.get("message", {}).get("content", "").strip()
        return ChatResponse(text=text or "I'm here.")


class LocalFallbackChatModel(ChatModel):
    def generate_reply(self, message: str, memory: ConversationMemory) -> ChatResponse:
        if message.endswith("?"):
            return ChatResponse(
                text="I can answer once Ollama is running locally. Start it, then ask me again."
            )
        if memory.recent_turns():
            return ChatResponse(text="I'm listening. Tell me what you'd like me to do next.")
        return ChatResponse(text="I'm ready when you are.")


class CompositeChatModel(ChatModel):
    def __init__(self, primary: ChatModel, fallback: ChatModel) -> None:
        self._primary = primary
        self._fallback = fallback

    def generate_reply(self, message: str, memory: ConversationMemory) -> ChatResponse:
        try:
            return self._primary.generate_reply(message=message, memory=memory)
        except RuntimeError:
            return self._fallback.generate_reply(message=message, memory=memory)
