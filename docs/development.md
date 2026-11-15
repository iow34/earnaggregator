# Development and verification

Use Python 3.11 and Node.js 24. Docker Compose is optional for local preview development.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pip check
python -m uvicorn demo.server:app --host 127.0.0.1 --port 8000
```

In a second terminal:

```bash
cd broadcast-admin-web
npm ci
VITE_PREVIEW_MODE=true npm run dev
```

Open http://localhost:5173. Vite proxies `/api` to the local preview. The preview mode flag is a build-time setting; do not enable it for a connected administrator deployment.

## Maintained checks

```bash
ruff check yield-data-service yield-telegram-bot demo tests scripts
python -m pytest tests -q
DATABASE_URL=postgresql+asyncpg://test:test@localhost/earn_test BOT_TOKEN=123456789:TEST_ONLY_NOT_A_REAL_BOT_TOKEN_000000000 PYTHONPATH=yield-telegram-bot python -m pytest yield-telegram-bot/tests -q
DATABASE_URL=postgresql+asyncpg://test:test@localhost/earn_test PYTHONPATH=yield-data-service python -m pytest yield-data-service/tests/models/test_models_pydantic.py yield-data-service/tests/models/test_models_response.py -q
cd broadcast-admin-web
npm run lint
npm run build
npm audit
```

The root tests cover the preview, operational authorization and fresh PostgreSQL schemas with hashed administrator keys. The database test requires `TEST_DATABASE_URL` pointing to a disposable local database with a name ending in `_test`; it creates and drops tables. Without that variable it is explicitly skipped. CI provides PostgreSQL and runs this check.

Historical provider-specific, API and storage tests also exist under `yield-data-service/tests/`. They require their own external services and fixtures and are not part of the maintained CI command above. Never run destructive integration fixtures against an existing deployment database. Current CI results should be used as the validation record, not old test-count claims.

## Dependency updates

`requirements.in` defines direct runtime constraints; `requirements.txt` locks their resolved versions. Development dependencies follow the same pattern. Regenerate both files with `uv pip compile`, install them in a fresh environment, run the maintained checks and `pip-audit -r requirements.txt`.

The npm lockfile is committed. A minimatch override selects the patched release for the TypeScript lint toolchain; keep this override under review when updating that toolchain.

## Adding an exchange

Use `yield-data-service/app/services/exchanges/example_exchange/` and the base adapter interfaces. Implement authentication and timeouts, normalize provider fields into yield products, expose the service from the package and add fixture-based tests. Verify the provider's current official endpoint and account permissions separately. Avoid real credentials in fixtures and recorded HTTP payloads.

Python comments focus on contracts and decisions; multilingual files under `bot/content` and `bot/localization` are product content and should retain their language variants.
