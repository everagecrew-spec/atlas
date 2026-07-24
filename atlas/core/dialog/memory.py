from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Deque


@dataclass(slots=True)
class Turn:
    role: str
    text: str


class ConversationMemory:
    def __init__(self, max_turns: int = 8) -> None:
        self._turns: Deque[Turn] = deque(maxlen=max_turns)

    def add(self, role: str, text: str) -> None:
        self._turns.append(Turn(role=role, text=text))

    def add_user(self, text: str) -> None:
        self.add("user", text)

    def add_assistant(self, text: str) -> None:
        self.add("assistant", text)

    def as_messages(self, system_prompt: str) -> list[dict[str, str]]:
        return [{"role": "system", "content": system_prompt}] + [
            {"role": turn.role, "content": turn.text} for turn in self._turns
        ]

    def recent_turns(self) -> list[Turn]:
        return list(self._turns)
