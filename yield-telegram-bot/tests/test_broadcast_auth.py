"""
Тести для сервісу авторизації адміністраторів.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from bot.broadcasts.auth import AdminAuthService


def test_password_hashing_and_verification():
    service = AdminAuthService()
    hashed = service.hash_password("secret")
    assert hashed != "secret"
    assert service.verify_password("secret", hashed) is True
    assert service.verify_password("invalid", hashed) is False


def test_api_key_generation_length():
    service = AdminAuthService()
    api_key = service.issue_api_key()
    assert len(api_key) == 64


@pytest.mark.asyncio
async def test_authenticate_api_key_fetches_admin():
    service = AdminAuthService()
    session = AsyncMock()
    fake_admin = MagicMock()
    with patch("bot.broadcasts.auth.crud.get_admin_by_api_key", AsyncMock(return_value=fake_admin)):
        result = await service.authenticate_api_key(session, "abc")
        assert result is fake_admin

