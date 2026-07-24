from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class AudioConfig:
    wake_word: str = "atlas"
    sample_rate: int = 16_000
    frame_ms: int = 30
    silence_ms: int = 900
    wake_threshold: float = 0.5
    listen_timeout_s: float = 8.0
    openwakeword_model_path: str | None = None


@dataclass(slots=True)
class STTConfig:
    provider: str = "faster_whisper"
    model: str = "base.en"
    device: str = "auto"
    compute_type: str = "int8"


@dataclass(slots=True)
class LLMConfig:
    provider: str = "ollama"
    host: str = "http://127.0.0.1:11434"
    model: str = "llama3.1:8b-instruct-q4_K_M"
    timeout_s: float = 30.0
    system_prompt: str = (
        "You are Atlas, a concise, thoughtful, privacy-first home assistant. "
        "Keep replies short, helpful, and natural."
    )


@dataclass(slots=True)
class TTSConfig:
    provider: str = "piper"
    command: str = "piper"
    voice: str | None = None
    extra_args: list[str] = field(default_factory=list)


@dataclass(slots=True)
class RuntimeConfig:
    max_turn_history: int = 8
    followup_window_s: float = 5.0
    confirm_risky_actions: bool = True
    dry_run: bool = False
    log_level: str = "INFO"


@dataclass(slots=True)
class HomeAssistantConfig:
    url: str = "http://homeassistant.local:8123"
    token_env_var: str = "HOME_ASSISTANT_TOKEN"
    verify_ssl: bool = True
    lights: dict[str, str] = field(default_factory=dict)
    thermostats: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class AtlasConfig:
    audio: AudioConfig = field(default_factory=AudioConfig)
    stt: STTConfig = field(default_factory=STTConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    tts: TTSConfig = field(default_factory=TTSConfig)
    runtime: RuntimeConfig = field(default_factory=RuntimeConfig)
    home_assistant: HomeAssistantConfig = field(default_factory=HomeAssistantConfig)
    env_file: Path = Path(".env")
