from __future__ import annotations

import json
import os
import ssl
import urllib.error
import urllib.request
from dataclasses import dataclass

from atlas.config.models import HomeAssistantConfig


@dataclass(slots=True)
class HomeAssistantServiceCall:
    domain: str
    service: str
    data: dict[str, object]


@dataclass(slots=True)
class LightPowerAction:
    entity_name: str
    power: str


@dataclass(slots=True)
class LightBrightnessAction:
    entity_name: str
    brightness_pct: int


@dataclass(slots=True)
class ThermostatSetTemperatureAction:
    entity_name: str
    temperature_f: float


class HomeAssistantClient:
    def __init__(self, config: HomeAssistantConfig, dry_run: bool = False) -> None:
        self._config = config
        self._dry_run = dry_run

    def _resolve_entity(self, entity_type: str, name: str) -> str:
        mapping = getattr(self._config, entity_type)
        key = name.strip().lower()
        if key not in mapping:
            raise KeyError(f"No Home Assistant mapping configured for {entity_type[:-1]} '{name}'.")
        return mapping[key]

    def to_service_call(
        self,
        action: LightPowerAction | LightBrightnessAction | ThermostatSetTemperatureAction,
    ) -> HomeAssistantServiceCall:
        if isinstance(action, LightPowerAction):
            entity_id = self._resolve_entity("lights", action.entity_name)
            return HomeAssistantServiceCall(
                domain="light",
                service=f"turn_{action.power}",
                data={"entity_id": entity_id},
            )
        if isinstance(action, LightBrightnessAction):
            entity_id = self._resolve_entity("lights", action.entity_name)
            return HomeAssistantServiceCall(
                domain="light",
                service="turn_on",
                data={"entity_id": entity_id, "brightness_pct": action.brightness_pct},
            )
        entity_id = self._resolve_entity("thermostats", action.entity_name)
        return HomeAssistantServiceCall(
            domain="climate",
            service="set_temperature",
            data={"entity_id": entity_id, "temperature": action.temperature_f},
        )

    def call_service(
        self,
        action: LightPowerAction | LightBrightnessAction | ThermostatSetTemperatureAction,
    ) -> HomeAssistantServiceCall:
        call = self.to_service_call(action)
        if self._dry_run:
            return call

        token = os.getenv(self._config.token_env_var)
        if not token:
            raise RuntimeError(
                f"Set {self._config.token_env_var} in your environment or .env file to call Home Assistant."
            )

        request = urllib.request.Request(
            url=f"{self._config.url.rstrip('/')}/api/services/{call.domain}/{call.service}",
            data=json.dumps(call.data).encode("utf-8"),
            headers={
                "Authorization": "Bearer " + token,
                "Content-Type": "application/json",
            },
            method="POST",
        )
        context = None if self._config.verify_ssl else ssl._create_unverified_context()
        try:
            with urllib.request.urlopen(request, context=context, timeout=10) as response:
                response.read()
        except urllib.error.URLError as exc:
            raise RuntimeError("Home Assistant service call failed. Check the local URL, token, and entity mappings.") from exc
        return call
