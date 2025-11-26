"""
Тести перевіряють структуру моделей БД для розсилок.
"""

from bot.db import models


def test_telegram_user_extended_fields_exist():
    user_columns = {column.name for column in models.TelegramUser.__table__.columns}

    assert {"is_subscribed", "tags", "last_active_at"} <= user_columns


def test_broadcast_tables_defined():
    for model_name in ("AdminUser", "Broadcast", "BroadcastRecipient", "BroadcastEvent"):
        assert hasattr(models, model_name), f"Model {model_name} відсутня"


def test_broadcast_model_columns():
    broadcast_columns = {c.name for c in models.Broadcast.__table__.columns}
    assert {
        "title",
        "content_type",
        "content_payload",
        "filter_query",
        "status",
        "scheduled_at",
        "approved_at",
    } <= broadcast_columns


def test_broadcast_recipient_columns():
    recipient_columns = {c.name for c in models.BroadcastRecipient.__table__.columns}
    assert {
        "status",
        "error_code",
        "attempts",
        "last_attempt_at",
        "message_id",
    } <= recipient_columns


def test_admin_user_has_security_fields():
    admin_columns = {c.name for c in models.AdminUser.__table__.columns}
    assert {"email", "password_hash", "role", "api_key"} <= admin_columns

