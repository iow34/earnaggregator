# API and authorization

The running API exposes its generated OpenAPI documentation at `/docs`. The connected data service and isolated preview are separate applications.

## Connected data service

Public catalogue routes under `/api/v1` include asset/product, top products and exchange read operations. Health is available at `/health` and `/api/v1/health`.

Mutations and operational diagnostics require `X-Service-API-Key`. Configure `SERVICE_API_KEY` on the API and on the bot. Tracking and user-activity reads/writes require the same service key. Missing configuration returns 503; a missing or incorrect supplied key returns 401. The old HTTP migration runner is removed.

```bash
curl --fail http://localhost:8000/api/v1/products
# For private operations, inject the key through your client or secret manager.
# Do not paste real authorization headers into documentation or issue reports.
```

## Broadcast administration API

Run `bot.admin_app:app` on port 8081. Requests use `X-Admin-API-Key`, issued by `scripts/create_admin.py`; this differs from the data-service key. Routes include:

| Method | Route | Purpose |
| --- | --- | --- |
| GET | `/broadcasts` | Paginated broadcast list |
| POST | `/broadcasts` | Create a broadcast |
| GET | `/broadcasts/metrics/summary` | Dashboard totals |
| GET | `/broadcasts/{id}` | Content, filters and delivery summary |
| POST | `/broadcasts/{id}/approve` | Owner approval |
| POST | `/broadcasts/{id}/cancel` | Cancel a job |
| POST | `/broadcasts/{id}/retry` | Retry delivery |
| GET | `/broadcasts/{id}/events` | Event history |
| GET | `/broadcasts/{id}/recipients` | Recipient statuses |

The frontend stores its key in sessionStorage for the current browser tab. This is still JavaScript-accessible storage; serve the administration interface only to trusted administrators over HTTPS, maintain a restrictive content security policy at the reverse proxy and do not embed third-party scripts.

## Preview API

The default preview exposes `/api/v1/products`, `/api/broadcasts`, `/api/broadcasts/metrics/summary` and broadcast detail/create routes. It accepts no production keys and does not deliver messages. Unknown detail IDs return 404; invalid input returns 422. At 100 preview broadcasts it refuses further creates until restart.
