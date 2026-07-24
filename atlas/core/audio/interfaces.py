from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(slots=True)
class SpeechInput:
    utterance: str | None = None
    raw_audio: bytes | None = None
    sample_rate: int = 16_000
    source: str = "unknown"


class WakeWordDetector(Protocol):
    def wait_for_wake_word(self) -> bool:
        ...


class UtteranceListener(Protocol):
    def listen_for_utterance(self) -> SpeechInput:
        ...
