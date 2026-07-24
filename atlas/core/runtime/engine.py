from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import StrEnum

from atlas.core.actions.home_assistant import (
    HomeAssistantClient,
    LightBrightnessAction,
    LightPowerAction,
    ThermostatSetTemperatureAction,
)
from atlas.core.actions.policy import ActionPolicy
from atlas.core.audio.interfaces import UtteranceListener, WakeWordDetector
from atlas.core.dialog.memory import ConversationMemory
from atlas.core.intents.router import IntentRouter
from atlas.core.llm.providers import ChatModel
from atlas.core.stt.providers import SpeechToText
from atlas.core.tts.providers import TextToSpeech


class AssistantState(StrEnum):
    IDLE = "idle"
    AWAKE = "awake"
    LISTENING = "listening"
    THINKING = "thinking"
    ACTING = "acting"
    SPEAKING = "speaking"


@dataclass(slots=True)
class RuntimeDependencies:
    wake_word: WakeWordDetector
    listener: UtteranceListener
    stt: SpeechToText
    router: IntentRouter
    memory: ConversationMemory
    llm: ChatModel
    tts: TextToSpeech
    actions: HomeAssistantClient
    policy: ActionPolicy


class AssistantRuntime:
    def __init__(self, deps: RuntimeDependencies, logger: logging.Logger) -> None:
        self._deps = deps
        self._logger = logger
        self._state = AssistantState.IDLE

    def run_forever(self, iterations: int | None = None) -> None:
        loops = 0
        while iterations is None or loops < iterations:
            self._set_state(AssistantState.IDLE)
            if not self._deps.wake_word.wait_for_wake_word():
                self._logger.info("event=shutdown reason=wake_word_exit")
                return

            self._set_state(AssistantState.AWAKE)
            self._speak("Yes?")

            self._set_state(AssistantState.LISTENING)
            speech = self._deps.listener.listen_for_utterance()

            self._set_state(AssistantState.THINKING)
            transcription = self._deps.stt.transcribe(speech)
            text = transcription.text.strip()
            self._logger.info("event=transcribed text=%r confidence=%s", text, transcription.confidence)

            if not text:
                self._speak("I didn't catch that.")
                loops += 1
                continue

            self._deps.memory.add_user(text)
            intent = self._deps.router.route(text)
            if intent.kind == "clarify":
                self._speak(intent.response or "Could you clarify that?")
                loops += 1
                continue
            if intent.kind == "action" and intent.action is not None:
                self._handle_action(intent.action)
                loops += 1
                continue

            reply = self._deps.llm.generate_reply(message=text, memory=self._deps.memory)
            self._deps.memory.add_assistant(reply.text)
            self._speak(reply.text)
            loops += 1

    def _handle_action(
        self,
        action: LightPowerAction | LightBrightnessAction | ThermostatSetTemperatureAction,
    ) -> None:
        decision = self._deps.policy.evaluate(action)
        if decision.requires_confirmation:
            self._speak(decision.prompt or "Please confirm.")
            # Hook point for interruption-ready confirmation flows.
            confirmation = self._deps.listener.listen_for_utterance()
            if not self._deps.router.is_affirmative(confirmation.utterance or ""):
                self._speak("Okay, I won't do that.")
                return

        self._set_state(AssistantState.ACTING)
        try:
            call = self._deps.actions.call_service(action)
        except (KeyError, RuntimeError) as exc:
            self._logger.warning("event=action_failed error=%s", exc)
            self._speak(str(exc))
            return
        if isinstance(action, LightPowerAction):
            reply = f"Okay — turning {action.power} {action.entity_name} lights."
        elif isinstance(action, LightBrightnessAction):
            reply = f"Okay — setting {action.entity_name} lights to {action.brightness_pct} percent."
        else:
            reply = f"Okay — setting {action.entity_name} thermostat to {action.temperature_f:.0f} degrees."
        self._logger.info(
            "event=action_executed domain=%s service=%s data=%s",
            call.domain,
            call.service,
            call.data,
        )
        self._deps.memory.add_assistant(reply)
        self._speak(reply)

    def _speak(self, text: str) -> None:
        self._set_state(AssistantState.SPEAKING)
        self._deps.tts.speak(text)

    def _set_state(self, state: AssistantState) -> None:
        previous = self._state
        self._state = state
        self._logger.info("event=state_transition previous=%s state=%s", previous, state)
