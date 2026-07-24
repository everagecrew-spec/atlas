from __future__ import annotations

import logging
import queue
from dataclasses import dataclass

from atlas.config.models import AudioConfig
from atlas.core.audio.interfaces import WakeWordDetector


class AudioDependencyError(RuntimeError):
    """Raised when optional audio dependencies are unavailable."""


@dataclass(slots=True)
class TextWakeWordDetector(WakeWordDetector):
    wake_word: str

    def wait_for_wake_word(self) -> bool:
        prompt = f"Type '{self.wake_word}' to wake Atlas (or 'quit' to exit): "
        while True:
            heard = input(prompt).strip().lower()
            if heard == "quit":
                return False
            if heard == self.wake_word.lower():
                return True
            print(f"Waiting for wake word '{self.wake_word}'.")


class OpenWakeWordDetector(WakeWordDetector):
    def __init__(self, config: AudioConfig, logger: logging.Logger) -> None:
        try:
            import sounddevice as sd
            from openwakeword.model import Model
        except ImportError as exc:
            raise AudioDependencyError(
                "Install atlas-assistant[audio,wakeword] to enable microphone wake-word detection."
            ) from exc

        self._config = config
        self._logger = logger
        self._sounddevice = sd
        model_paths = [config.openwakeword_model_path] if config.openwakeword_model_path else None
        try:
            self._model = Model(wakeword_models=model_paths)
        except Exception as exc:  # pragma: no cover - depends on local assets
            raise AudioDependencyError(
                "openWakeWord model assets are unavailable. Provide audio.openwakeword_model_path for a custom 'Atlas' model or use --text-mode."
            ) from exc

    def wait_for_wake_word(self) -> bool:
        audio_queue: queue.Queue = queue.Queue()

        def callback(indata, frames, _time_info, status) -> None:  # pragma: no cover - device callback
            if status:
                self._logger.warning("event=wake_word_audio_status status=%s", status)
            audio_queue.put(indata.copy())

        with self._sounddevice.InputStream(
            channels=1,
            samplerate=self._config.sample_rate,
            dtype="int16",
            blocksize=int(self._config.sample_rate * self._config.frame_ms / 1000),
            callback=callback,
        ):
            while True:
                chunk = audio_queue.get().reshape(-1)
                predictions = self._model.predict(chunk)
                score = max(predictions.values(), default=0.0)
                if score >= self._config.wake_threshold:
                    self._logger.info("event=wake_word_detected provider=openwakeword score=%.3f", score)
                    return True


class WakeWordDetectorFactory:
    @staticmethod
    def build(config: AudioConfig, logger: logging.Logger, force_text_mode: bool = False) -> WakeWordDetector:
        if force_text_mode:
            logger.info("event=wake_word_mode mode=text reason=forced")
            return TextWakeWordDetector(wake_word=config.wake_word)
        try:
            return OpenWakeWordDetector(config=config, logger=logger)
        except AudioDependencyError as exc:
            logger.warning("event=wake_word_fallback mode=text detail=%s", exc)
            return TextWakeWordDetector(wake_word=config.wake_word)
