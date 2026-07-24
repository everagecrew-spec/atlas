import unittest

from atlas.config.models import HomeAssistantConfig
from atlas.core.actions.home_assistant import (
    HomeAssistantClient,
    LightBrightnessAction,
    LightPowerAction,
    ThermostatSetTemperatureAction,
)


class HomeAssistantMappingTests(unittest.TestCase):
    def setUp(self) -> None:
        config = HomeAssistantConfig(
            lights={"living room": "light.living_room", "kitchen": "light.kitchen"},
            thermostats={"downstairs": "climate.downstairs"},
        )
        self.client = HomeAssistantClient(config=config, dry_run=True)

    def test_maps_light_power_to_service_call(self) -> None:
        call = self.client.to_service_call(LightPowerAction(entity_name="living room", power="on"))
        self.assertEqual(call.domain, "light")
        self.assertEqual(call.service, "turn_on")
        self.assertEqual(call.data, {"entity_id": "light.living_room"})

    def test_maps_brightness_to_service_call(self) -> None:
        call = self.client.to_service_call(LightBrightnessAction(entity_name="kitchen", brightness_pct=45))
        self.assertEqual(call.domain, "light")
        self.assertEqual(call.service, "turn_on")
        self.assertEqual(call.data, {"entity_id": "light.kitchen", "brightness_pct": 45})

    def test_maps_thermostat_to_service_call(self) -> None:
        call = self.client.to_service_call(ThermostatSetTemperatureAction(entity_name="downstairs", temperature_f=70))
        self.assertEqual(call.domain, "climate")
        self.assertEqual(call.service, "set_temperature")
        self.assertEqual(call.data, {"entity_id": "climate.downstairs", "temperature": 70})

    def test_raises_for_unknown_entity(self) -> None:
        with self.assertRaises(KeyError):
            self.client.to_service_call(LightPowerAction(entity_name="office", power="off"))


if __name__ == "__main__":
    unittest.main()
