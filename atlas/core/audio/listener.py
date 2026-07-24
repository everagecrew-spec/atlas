from __future__ import annotations

import logging
import queue
import time
from dataclasses import dataclass

from atlas.config.models import AudioConfig
from atlas.core.audio.interfaces import SpeechInput, UtteranceListener
from atlas.core.audio.wakeword import AudioDependencyError


@dataclass(slots=True)
class TextUtteranceListener(UtteranceListener):
    def listen_for_utterance(self) -> SpeechInput:
        utterance = input("What can I help with? ").strip()
        return SpeechInput(utterance=utterance, source="text")


class VADUtteranceListener(UtteranceListener):
    def __init__(self, config: AudioConfig, logger: logging.Logger) -> None:
        try:
            import sounddevice as sd
            import webrtcvad
        except ImportError as exc:
            raise AudioDependencyError(
                "Install atlas-assistant[audio] to enable microphone capture with VAD."
            ) from exc

        self._config = config
        self._logger = logger
        self._sounddevice = sd
        self._vad = webrtcvad.Vad(2)

    def listen_for_utterance(self) -> SpeechInput:
        frame_bytes = int(self._config.sample_rate * self._config.frame_ms / 1000) * 2
        silence_limit = max(1, int(self._config.silence_ms / self._config.frame_ms))
        audio_queue: queue.Queue[bytes] = queue.Queue()
        frames: list[bytes] = []
        silence_frames = 0
        heard_speech = False
        started = time.monotonic()

        def callback(indata, _frames_count, _time_info, status) -> None:  # pragma: no cover - device callback
            if status:
                self._logger.warning("event=listener_audio_status status=%s", status)
            audio_queue.put(bytes(indata))

        with self._sounddevice.RawInputStream(
            channels=1,
            samplerate=self._config.sample_rate,
            dtype="int16",
            blocksize=frame_bytes // 2,
            callback=callback,
        ):
            while time.monotonic() - started < self._config.listen_timeout_s:
                chunk = audio_queue.get()
                if len(chunk) != frame_bytes:
                    continue
                is_speech = self._vad.is_speech(chunk, self._config.sample_rate)
                if is_speech:
                    heard_speech = True
                    silence_frames = 0
                    frames.append(chunk)
                elif heard_speech:
                    frames.append(chunk)
                    silence_frames += 1
                    if silence_frames >= silence_limit:
                        break

        raw_audio = b"".join(frames)
        self._logger.info(
            "event=utterance_captured source=microphone frames=%d bytes=%d",
            len(frames),
            len(raw_audio),
        )
        return SpeechInput(raw_audio=raw_audio, sample_rate=self._config.sample_rate, source="microphone")


class UtteranceListenerFactory:
    @staticmethod
    def build(config: AudioConfig, logger: logging.Logger, force_text_mode: bool = False) -> UtteranceListener:
        if force_text_mode:
            logger.info("event=listener_mode mode=text reason=forced")
            return TextUtteranceListener()
        try:
            return VADUtteranceListener(config=config, logger=logger)
        except AudioDependencyError as exc:
            logger.warning("event=listener_fallback mode=text detail=%s", exc)
            return TextUtteranceListener()
