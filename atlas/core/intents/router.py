from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from atlas.core.actions.home_assistant import (
    LightBrightnessAction,
    LightPowerAction,
    ThermostatSetTemperatureAction,
)

Action = LightPowerAction | LightBrightnessAction | ThermostatSetTemperatureAction
IntentKind = Literal["action", "chat", "clarify"]


@dataclass(slots=True)
class Intent:
    kind: IntentKind
    confidence: float
    action: Action | None = None
    response: str | None = None


class IntentRouter:
    POWER_PATTERN = re.compile(
        r"(?:turn|switch)\s+(?P<power>on|off)\s+(?:the\s+)?(?P<name>[a-z0-9\s]+?)\s+lights?$",
        re.IGNORECASE,
    )
    BRIGHTNESS_PATTERN = re.compile(
        r"(?:set|dim)\s+(?:the\s+)?(?P<name>[a-z0-9\s]+?)\s+lights?(?:\s+to)?\s+(?P<level>\d{1,3})(?:\s*percent)?$",
        re.IGNORECASE,
    )
    THERMOSTAT_PATTERN = re.compile(
        r"set\s+(?:the\s+)?(?P<name>[a-z0-9\s]+?)\s+thermostat(?:\s+to)?\s+(?P<temp>\d{2,3})(?:\s*degrees?)?$",
        re.IGNORECASE,
    )

    def route(self, utterance: str) -> Intent:
        normalized = " ".join(utterance.strip().split())
        if not normalized:
            return Intent(kind="clarify", confidence=0.0, response="I didn't catch that. Could you say it again?")

        # Integrators can expand these patterns to add new smart-home intents.
        if match := self.POWER_PATTERN.match(normalized):
            return Intent(
                kind="action",
                confidence=0.96,
                action=LightPowerAction(
                    entity_name=match.group("name").strip().lower(),
                    power=match.group("power").lower(),
                ),
            )
        if match := self.BRIGHTNESS_PATTERN.match(normalized):
            level = max(0, min(100, int(match.group("level"))))
            return Intent(
                kind="action",
                confidence=0.94,
                action=LightBrightnessAction(
                    entity_name=match.group("name").strip().lower(),
                    brightness_pct=level,
                ),
            )
        if match := self.THERMOSTAT_PATTERN.match(normalized):
            return Intent(
                kind="action",
                confidence=0.95,
                action=ThermostatSetTemperatureAction(
                    entity_name=match.group("name").strip().lower(),
                    temperature_f=float(match.group("temp")),
                ),
            )

        has_action_indicators = any(
            keyword in normalized.lower() for keyword in ("turn", "switch", "set", "dim", "lights", "thermostat")
        )
        if has_action_indicators:
            return Intent(
                kind="clarify",
                confidence=0.45,
                response="Do you want me to control a light or set a thermostat?",
            )
        return Intent(kind="chat", confidence=0.65)

    @staticmethod
    def is_affirmative(text: str) -> bool:
        return text.strip().lower() in {"yes", "y", "confirm", "do it", "go ahead"}
