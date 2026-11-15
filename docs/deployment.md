# Connected deployment

The default `docker compose up` runs an isolated product preview. Use `docker-compose.prod.yml` explicitly to configure the connected services. No hosted endpoint is included with this repository.

1. Copy `.env.example` to `.env`; replace the PostgreSQL password and DSN, set a fresh service key, and provide the bot token and required exchange credentials.
2. Review origins and external URLs. Keep Redis/PostgreSQL on a private network. Bind application ports to loopback and put an authenticated HTTPS reverse proxy in front of the administration API.
3. Start storage, build the application image, then initialize the fresh schema:

```bash
docker compose -f docker-compose.prod.yml up -d postgres redis
docker compose -f docker-compose.prod.yml build yield-api
docker compose -f docker-compose.prod.yml run --rm yield-api python scripts/init_database.py
```

The initializer creates both service schemas on a **fresh** database. It does not migrate existing columns. For an existing installation, take a backup and create/review an Alembic migration against the actual schema. The historic Alembic revisions describe earlier broadcast changes and are not a replacement for the fresh schema initializer.

4. Start the data service:

```bash
docker compose -f docker-compose.prod.yml up -d yield-api
```

5. Provision a broadcast owner. The command asks for a password without echoing it and displays its new API key once. Run it in a private terminal; only the key digest is stored.

```bash
docker compose -f docker-compose.prod.yml run --rm yield-api python scripts/create_admin.py
```

Existing administrator keys from earlier versions must be reissued: the `api_key` column now stores SHA-256 digests. Do not migrate plaintext keys by publishing them in a script or SQL fixture.

6. Enable only the services you need:

```bash
docker compose -f docker-compose.prod.yml --profile telegram up -d
docker compose -f docker-compose.prod.yml --profile broadcasts up -d
```

The connected admin UI can be built with `VITE_PREVIEW_MODE=false` and a reverse proxy forwarding `/api/` to the administration API. The included production nginx configuration targets `broadcast-admin:8081` inside the same Docker network.

7. Verify schema, authorized API operations, shutdown behavior, provider access and worker delivery using a controlled test recipient before making the connected system available. Do not promise exactly-once delivery across worker restarts.

Monitoring configuration remains in `yield-data-service/monitoring/`. Add it behind your own private gateway with unique credentials rather than exposing default dashboards publicly.
