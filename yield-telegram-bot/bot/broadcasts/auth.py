from __future__ import annotations

import secrets
from enum import Enum
from typing import Optional

import bcrypt
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db import crud
from bot.db.models import AdminUser


class AdminRole(str, Enum):
    OPERATOR = "operator"
    OWNER = "owner"


class AdminAuthService:
    def __init__(self) -> None:
        pass

    def hash_password(self, password: str) -> str:
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("ascii")

    def verify_password(self, password: str, hashed: str) -> bool:
        try:
            return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("ascii"))
        except (ValueError, UnicodeError):
            return False

    def issue_api_key(self) -> str:
        return secrets.token_hex(32)

    async def authenticate_api_key(
        self,
        session: AsyncSession,
        api_key: str,
    ) -> Optional[AdminUser]:
        return await crud.get_admin_by_api_key(session, api_key)

    async def register_admin(
        self,
        session: AsyncSession,
        *,
        email: str,
        password: str,
        role: AdminRole = AdminRole.OPERATOR,
    ) -> AdminUser:
        existing = await crud.get_admin_by_email(session, email)
        if existing:
            return existing

        password_hash = self.hash_password(password)
        api_key = self.issue_api_key()

        return await crud.create_admin_user(
            session,
            email=email,
            password_hash=password_hash,
            api_key=api_key,
            role=role.value,
        )


admin_auth_service = AdminAuthService()
