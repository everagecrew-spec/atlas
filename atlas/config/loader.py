from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from atlas.config.models import AtlasConfig, AudioConfig, HomeAssistantConfig, LLMConfig, RuntimeConfig, STTConfig, TTSConfig


class ConfigError(RuntimeError):
    """Raised when Atlas configuration is invalid."""


def load_env_file(path: str | Path) -> None:
    env_path = Path(path)
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def _section(data: dict[str, Any], key: str) -> dict[str, Any]:
    section = data.get(key, {}) or {}
    if not isinstance(section, dict):
        raise ConfigError(f"Expected '{key}' to be a mapping.")
    return section


def load_config(path: str | Path) -> AtlasConfig:
    config_path = Path(path)
    if not config_path.exists():
        raise ConfigError(f"Config file not found: {config_path}")

    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ConfigError("Top-level config must be a mapping.")

    config = AtlasConfig(
        audio=AudioConfig(**_section(raw, "audio")),
        stt=STTConfig(**_section(raw, "stt")),
        llm=LLMConfig(**_section(raw, "llm")),
        tts=TTSConfig(**_section(raw, "tts")),
        runtime=RuntimeConfig(**_section(raw, "runtime")),
        home_assistant=HomeAssistantConfig(**_section(raw, "home_assistant")),
        env_file=Path(raw.get("env_file", ".env")),
    )
    load_env_file(config.env_file)
    return config
