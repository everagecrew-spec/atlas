from __future__ import annotations

import logging
from dataclasses import dataclass

from atlas.config.models import STTConfig
from atlas.core.audio.interfaces import SpeechInput


@dataclass(slots=True)
class Transcription:
    text: str
    confidence: float | None = None


class SpeechToText:
    def transcribe(self, speech: SpeechInput) -> Transcription:
        raise NotImplementedError


class PassthroughSpeechToText(SpeechToText):
    def transcribe(self, speech: SpeechInput) -> Transcription:
        return Transcription(text=(speech.utterance or "").strip(), confidence=1.0)


class FasterWhisperSpeechToText(SpeechToText):
    def __init__(self, config: STTConfig) -> None:
        try:
            import numpy as np
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise RuntimeError(
                "Install atlas-assistant[stt] to enable local faster-whisper transcription."
            ) from exc
        self._np = np
        self._model = WhisperModel(config.model, device=config.device, compute_type=config.compute_type)

    def transcribe(self, speech: SpeechInput) -> Transcription:
        if speech.utterance is not None:
            return Transcription(text=speech.utterance.strip(), confidence=1.0)
        if not speech.raw_audio:
            return Transcription(text="", confidence=0.0)
        audio = self._np.frombuffer(speech.raw_audio, dtype=self._np.int16).astype(self._np.float32) / 32768.0
        segments, info = self._model.transcribe(audio, language="en")
        text = " ".join(segment.text.strip() for segment in segments).strip()
        return Transcription(text=text, confidence=getattr(info, "language_probability", None))


class SpeechToTextFactory:
    @staticmethod
    def build(config: STTConfig, logger: logging.Logger, force_text_mode: bool = False) -> SpeechToText:
        if force_text_mode:
            logger.info("event=stt_mode mode=passthrough reason=forced")
            return PassthroughSpeechToText()
        try:
            return FasterWhisperSpeechToText(config=config)
        except RuntimeError as exc:
            logger.warning("event=stt_fallback mode=passthrough detail=%s", exc)
            return PassthroughSpeechToText()
