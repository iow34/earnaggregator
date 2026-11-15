"""Issue a broadcast administrator key. Run locally; keep stdout private."""

import asyncio
from getpass import getpass
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "yield-telegram-bot"))
from bot.broadcasts.auth import AdminAuthService, AdminRole
from bot.db.crud import create_admin_user, get_admin_by_email
from bot.db.database import db_manager


async def create() -> None:
    email = input("Administrator email: ").strip()
    password = getpass("Password (at least 12 characters): ")
    if len(password) < 12 or len(password.encode()) > 72 or "@" not in email:
        raise ValueError("Provide a valid email and a password of at least 12 characters")
    if not await db_manager.initialize():
        raise RuntimeError("Database initialization failed")
    try:
        async with db_manager.get_session() as session:
            if await get_admin_by_email(session, email):
                raise ValueError("Administrator already exists")
            auth = AdminAuthService()
            key = auth.issue_api_key()
            await create_admin_user(
                session,
                email=email,
                password_hash=auth.hash_password(password),
                api_key=key,
                role=AdminRole.OWNER.value,
            )
            await session.commit()
            print("Save this key now; only its SHA-256 digest is stored:")
            print(key)
    finally:
        await db_manager.close_engine()


if __name__ == "__main__":
    asyncio.run(create())
