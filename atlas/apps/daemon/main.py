from __future__ import annotations

import argparse
import logging
from pathlib import Path

from atlas.config.loader import load_config, load_env_file
from atlas.core.actions.home_assistant import HomeAssistantClient
from atlas.core.actions.policy import ActionPolicy
from atlas.core.audio.listener import UtteranceListenerFactory
from atlas.core.audio.wakeword import WakeWordDetectorFactory
from atlas.core.dialog.memory import ConversationMemory
from atlas.core.intents.router import IntentRouter
from atlas.core.llm.providers import CompositeChatModel, LocalFallbackChatModel, OllamaChatModel
from atlas.core.runtime.engine import AssistantRuntime, RuntimeDependencies
from atlas.core.stt.providers import SpeechToTextFactory
from atlas.core.tts.providers import TextToSpeechFactory


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the Atlas local-first assistant daemon.")
    parser.add_argument("--config", default="config/atlas.example.yaml", help="Path to Atlas YAML config")
    parser.add_argument("--env-file", default=None, help="Optional override for the env file path")
    parser.add_argument("--once", action="store_true", help="Run a single wake/listen/respond cycle")
    parser.add_argument("--text-mode", action="store_true", help="Force keyboard I/O instead of microphone/audio backends")
    parser.add_argument("--dry-run", action="store_true", help="Log Home Assistant service calls without sending them")
    parser.add_argument("--log-level", default=None, help="Override the configured log level")
    return parser


def configure_logging(level: str) -> logging.Logger:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    return logging.getLogger("atlas")


def main() -> int:
    args = build_parser().parse_args()
    config = load_config(Path(args.config))
    if args.env_file:
        load_env_file(args.env_file)
        config.env_file = Path(args.env_file)
    if args.dry_run:
        config.runtime.dry_run = True
    if args.log_level:
        config.runtime.log_level = args.log_level

    logger = configure_logging(config.runtime.log_level)

    # Integrators can swap these factories to add custom wake word, STT, TTS, or intent providers.
    deps = RuntimeDependencies(
        wake_word=WakeWordDetectorFactory.build(config.audio, logger, force_text_mode=args.text_mode),
        listener=UtteranceListenerFactory.build(config.audio, logger, force_text_mode=args.text_mode),
        stt=SpeechToTextFactory.build(config.stt, logger, force_text_mode=args.text_mode),
        router=IntentRouter(),
        memory=ConversationMemory(max_turns=config.runtime.max_turn_history),
        llm=CompositeChatModel(primary=OllamaChatModel(config.llm), fallback=LocalFallbackChatModel()),
        tts=TextToSpeechFactory.build(config.tts, logger, force_text_mode=args.text_mode),
        actions=HomeAssistantClient(config.home_assistant, dry_run=config.runtime.dry_run),
        policy=ActionPolicy(confirm_risky_actions=config.runtime.confirm_risky_actions),
    )
    AssistantRuntime(deps=deps, logger=logger).run_forever(iterations=1 if args.once else None)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
