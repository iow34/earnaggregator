"""
Сервіс авторизації адміністраторів для ручних розсилок.
"""

from __future__ import annotations

import secrets
from enum import Enum
from typing import Optional

try:
    from passlib.context import CryptContext
except ImportError:  # pragma: no cover - fallback для середовищ без passlib
    import hashlib

    class CryptContext:  # type: ignore
        def __init__(self, *args, **kwargs):
            self._salt = kwargs.get("salt", "earnaggregator")

        def hash(self, password: str) -> str:
            return hashlib.sha256((password + self._salt).encode("utf-8")).hexdigest()

        def verify(self, password: str, hashed: str) -> bool:
            return self.hash(password) == hashed
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db import crud
from bot.db.models import AdminUser


class AdminRole(str, Enum):
    OPERATOR = "operator"
    OWNER = "owner"


class AdminAuthService:
    """Інструменти для керування адміністраторами."""

    def __init__(self) -> None:
        self._pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def hash_password(self, password: str) -> str:
        return self._pwd_context.hash(password)

    def verify_password(self, password: str, hashed: str) -> bool:
        return self._pwd_context.verify(password, hashed)

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

