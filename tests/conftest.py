"""Non-secret defaults for isolated tests; CI supplies disposable services."""

import os

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/earn_test")
os.environ.setdefault("BOT_TOKEN", "123456789:TEST_ONLY_NOT_A_REAL_BOT_TOKEN_000000000")
os.environ.setdefault("DEPLOY_ENV", "development")
