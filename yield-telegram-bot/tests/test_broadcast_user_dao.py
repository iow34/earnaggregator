import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from bot.db import crud


@pytest.mark.asyncio
async def test_update_user_subscription_invokes_commit():
    session = AsyncMock()
    session.execute.return_value = SimpleNamespace(rowcount=1)

    await crud.update_user_subscription(session, telegram_id=1, is_subscribed=False)

    session.execute.assert_called_once()
    session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_update_user_tags_merges_and_commits():
    session = AsyncMock()
    existing_user = MagicMock(tags=["premium"])

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_user
    session.execute.return_value = mock_result

    await crud.add_user_tags(session, telegram_id=1, tags=["vip"])

    session.execute.assert_called()
    session.commit.assert_called_once()
    assert existing_user.tags == ["premium", "vip"]


@pytest.mark.asyncio
async def test_filter_users_for_broadcast_returns_rows():
    session = AsyncMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [MagicMock(telegram_id=1)]
    mock_result = MagicMock()
    mock_result.scalars.return_value = mock_scalars
    session.execute.return_value = mock_result

    result = await crud.filter_users_for_broadcast(
        session,
        filters={"is_subscribed": True, "languages": ["ua"], "tags_all": ["vip"]},
        limit=100,
    )

    session.execute.assert_called_once()
    assert len(result) == 1
