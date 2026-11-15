from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Sequence, Set


@dataclass(frozen=True, slots=True)
class BroadcastScenario:
    channel: str
    description: str
    allowed_content_types: Set[str]
    supports_preview: bool = True
    requires_approval: bool = False
    default_batch_size: int = 100
    metadata: dict = field(default_factory=dict)

    def requires_secondary_confirmation(self) -> bool:
        return self.requires_approval


def _build_scenarios() -> List[BroadcastScenario]:
    base_types: Sequence[str] = ("text", "markdown", "html", "photo", "document")

    return [
        BroadcastScenario(
            channel="web_ui",
            description="",
            allowed_content_types=set(base_types),
            supports_preview=True,
            requires_approval=True,
            default_batch_size=150,
            metadata={
                "roles": ("operator", "owner"),
                "ui": {"preview_chat": "TEST_CHANNEL", "schedule": True},
            },
        ),
        BroadcastScenario(
            channel="cli",
            description="",
            allowed_content_types=set(base_types),
            supports_preview=True,
            requires_approval=False,
            default_batch_size=100,
            metadata={
                "cli_command": "python -m bot.cli.broadcast",
                "api_endpoint": "/broadcasts",
            },
        ),
        BroadcastScenario(
            channel="admin_bot",
            description="",
            allowed_content_types=set(base_types),
            supports_preview=True,
            requires_approval=True,
            default_batch_size=80,
            metadata={
                "whitelist_env": "ADMIN_WHITELIST_IDS",
                "fsm": True,
                "anti_flood": True,
            },
        ),
    ]


BROADCAST_SCENARIOS: List[BroadcastScenario] = _build_scenarios()
