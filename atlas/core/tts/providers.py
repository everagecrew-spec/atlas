from __future__ import annotations

import logging
import shutil
import subprocess

from atlas.config.models import TTSConfig


class TextToSpeech:
    def speak(self, text: str) -> None:
        raise NotImplementedError


class ConsoleTextToSpeech(TextToSpeech):
    def speak(self, text: str) -> None:
        print(f"Atlas: {text}")


class PiperTextToSpeech(TextToSpeech):
    def __init__(self, config: TTSConfig) -> None:
        command_path = shutil.which(config.command)
        if not command_path:
            raise RuntimeError(
                f"Piper command '{config.command}' was not found. Install Piper or use console fallback."
            )
        self._command = command_path
        self._voice = config.voice
        self._extra_args = list(config.extra_args)

    def speak(self, text: str) -> None:
        command = [self._command, *self._extra_args]
        if self._voice:
            command.extend(["--model", self._voice])
        subprocess.run(command, input=text.encode("utf-8"), check=True)


class TextToSpeechFactory:
    @staticmethod
    def build(config: TTSConfig, logger: logging.Logger, force_text_mode: bool = False) -> TextToSpeech:
        if force_text_mode:
            logger.info("event=tts_mode mode=console reason=forced")
            return ConsoleTextToSpeech()
        try:
            return PiperTextToSpeech(config=config)
        except RuntimeError as exc:
            logger.warning("event=tts_fallback mode=console detail=%s", exc)
            return ConsoleTextToSpeech()
