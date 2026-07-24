from __future__ import annotations

from dataclasses import dataclass

from atlas.core.actions.home_assistant import (
    LightBrightnessAction,
    LightPowerAction,
    ThermostatSetTemperatureAction,
)


@dataclass(slots=True)
class PolicyDecision:
    requires_confirmation: bool
    prompt: str | None = None
    reason: str | None = None


class ActionPolicy:
    def __init__(self, confirm_risky_actions: bool = True) -> None:
        self._confirm_risky_actions = confirm_risky_actions

    def evaluate(
        self,
        action: LightPowerAction | LightBrightnessAction | ThermostatSetTemperatureAction,
    ) -> PolicyDecision:
        if not self._confirm_risky_actions:
            return PolicyDecision(requires_confirmation=False)
        if isinstance(action, ThermostatSetTemperatureAction) and not 60 <= action.temperature_f <= 80:
            return PolicyDecision(
                requires_confirmation=True,
                prompt=f"That temperature is {action.temperature_f:.0f} degrees. Should I continue?",
                reason="extreme_temperature",
            )
        return PolicyDecision(requires_confirmation=False)
