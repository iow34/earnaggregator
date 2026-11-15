import pytest


def test_scenarios_module_exposes_expected_structures():
    from bot.broadcasts import scenarios

    assert hasattr(scenarios, "BroadcastScenario")
    assert hasattr(scenarios, "BROADCAST_SCENARIOS")


def test_scenarios_cover_all_channels():
    from bot.broadcasts.scenarios import BROADCAST_SCENARIOS

    channels = {scenario.channel for scenario in BROADCAST_SCENARIOS}
    assert {"web_ui", "cli", "admin_bot"} <= channels


def test_scenarios_support_required_message_types():
    from bot.broadcasts.scenarios import BROADCAST_SCENARIOS

    supported_types = set()
    for scenario in BROADCAST_SCENARIOS:
        supported_types.update(scenario.allowed_content_types)

    assert {"text", "markdown", "html", "photo", "document"} <= supported_types


@pytest.mark.parametrize("channel", ["web_ui", "cli", "admin_bot"])
def test_each_channel_has_preview_capability(channel: str):
    from bot.broadcasts.scenarios import BROADCAST_SCENARIOS

    scenario = next(s for s in BROADCAST_SCENARIOS if s.channel == channel)
    assert scenario.supports_preview is True
