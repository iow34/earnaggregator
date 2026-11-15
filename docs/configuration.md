# Configuration

The credential-free preview needs no `.env`. Copy `.env.example` only for a connected deployment.

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | PostgreSQL SQLAlchemy URL; use the asyncpg driver |
| `POSTGRES_PASSWORD` | Compose PostgreSQL initialization password |
| `REDIS_URL` | Private Redis URL for cache/queue |
| `SERVICE_API_KEY` | Shared key for private data API operations and bot tracking |
| `BOT_TOKEN` | Telegram token, required by bot configuration |
| `DATA_SERVICE_URL` | Bot's data-service base URL |
| `TRACKING_REDIRECT_URL` | Externally reachable URL for connected referral navigation |
| `DEPLOY_ENV` | Set `prod` for the bot's production URL validation |
| `ENVIRONMENT` | Data-service environment name |
| `ALLOWED_ORIGINS` | JSON list of data-service browser origins |
| `BROADCAST_ADMIN_ALLOWED_ORIGINS` | JSON list of admin UI origins |
| `SERVICE_NAME` | Container entrypoint selection |

The full set of exchange credentials, referral settings, queue limits and refresh intervals is defined in the two service configuration modules. Leave unused exchange credentials empty. Use read-only account permissions wherever sufficient; never enable trading or withdrawal rights just to display products.

Generate service secrets locally using a password manager or `python -c 'import secrets; print(secrets.token_urlsafe(32))'`. Keep the result out of Git, screenshots and support tickets.

When a database password contains reserved URL characters, URL-encode the password segment before building the DSN. The PostgreSQL password in Compose and its URL-encoded representation in `DATABASE_URL` must refer to the same value.

The browser variables `VITE_BROADCAST_API_URL` and `VITE_PREVIEW_MODE` are public build-time settings. Never place credentials in a `VITE_*` variable.
