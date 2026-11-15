# Architecture

## Data collection and normalization

Each exchange adapter implements API access and product conversion behind a common service interface. The registry discovers exchange modules and exposes their service instances to aggregation. Source-specific authentication, timeouts and response shapes belong in the adapters; the API consumes normalized yield products.

APY is expressed as a percentage. Lock periods use days, with zero representing a flexible product. Provider-specific raw payloads can be retained for inspection. Some sources use public web endpoints or imported snapshots; a directory in the registry is not a guarantee that the provider currently exposes a compatible endpoint.

PostgreSQL stores catalogue records, raw exchange data, priority/trending products and tracking events. Redis caches responses and is also used by the broadcast queue. Scheduled jobs refresh products and popularity data; the API exposes health and metric endpoints.

## Telegram experience

The aiogram service renders product comparisons, exchange navigation and recommendations. Content is localized into English, Ukrainian and Russian. Language preference is persisted and propagated through stateful navigation. Static and dynamic referral navigation are separate from product normalization.

The bot sends `X-Service-API-Key` for private data-service requests. Tracking and user activity are service-to-service operations rather than public catalogue endpoints.

## Broadcast workflow

The admin API authenticates `X-Admin-API-Key` against SHA-256 digests in PostgreSQL. Password verification uses bcrypt. A separate CLI issues an owner key once; plaintext keys are never stored in the administrator table.

Broadcasts persist content, filters, recipient state and delivery events. Owner approval gates approval-sensitive jobs. The Redis worker performs delivery, retry handling and metrics updates; the scheduler queues due jobs. The web interface focuses on composing and inspecting broadcasts; the API also exposes approval, cancellation and retry operations.

Queue delivery and database updates do not form one distributed transaction. Validate restart/retry behavior for the chosen delivery requirements. Do not assume exactly-once Telegram delivery.

## Interactive preview

`demo/server.py` owns synthetic products and in-memory draft broadcasts. Each app instance has independent state. No credentials, database, exchange adapter, queue consumer or Telegram client is used. The preview mirrors the administration API's list/detail/create shapes so reviewers can explore the UI safely.

The preview banner identifies synthetic rates and disabled delivery. It never claims that saving a draft sends a real message.

## Boundaries and deployment

Public catalogue reads are available without an operational key. Mutations, diagnostics and tracking require `X-Service-API-Key`; the service fails closed when no key is configured. Database initialization is a local CLI operation, not an HTTP endpoint.

The default Compose file runs the isolated preview on loopback ports. Connected services use the explicit production Compose file and environment configuration. No private deployment is automatically started from a GitHub push.
