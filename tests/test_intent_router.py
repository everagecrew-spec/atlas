import unittest

from atlas.core.actions.home_assistant import LightBrightnessAction, LightPowerAction, ThermostatSetTemperatureAction
from atlas.core.intents.router import IntentRouter


class IntentRouterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.router = IntentRouter()

    def test_routes_light_power_commands(self) -> None:
        intent = self.router.route("turn off living room lights")
        self.assertEqual(intent.kind, "action")
        self.assertIsInstance(intent.action, LightPowerAction)
        self.assertEqual(intent.action.entity_name, "living room")
        self.assertEqual(intent.action.power, "off")

    def test_routes_light_brightness_commands(self) -> None:
        intent = self.router.route("dim kitchen lights to 30 percent")
        self.assertEqual(intent.kind, "action")
        self.assertIsInstance(intent.action, LightBrightnessAction)
        self.assertEqual(intent.action.entity_name, "kitchen")
        self.assertEqual(intent.action.brightness_pct, 30)

    def test_routes_thermostat_commands(self) -> None:
        intent = self.router.route("set downstairs thermostat to 72 degrees")
        self.assertEqual(intent.kind, "action")
        self.assertIsInstance(intent.action, ThermostatSetTemperatureAction)
        self.assertEqual(intent.action.entity_name, "downstairs")
        self.assertEqual(intent.action.temperature_f, 72.0)

    def test_asks_for_clarification_when_command_is_ambiguous(self) -> None:
        intent = self.router.route("set it to 50")
        self.assertEqual(intent.kind, "clarify")
        self.assertIn("light or set a thermostat", intent.response)

    def test_defaults_to_chat_for_non_command_input(self) -> None:
        intent = self.router.route("how was your day?")
        self.assertEqual(intent.kind, "chat")
        self.assertIsNone(intent.action)


if __name__ == "__main__":
    unittest.main()
