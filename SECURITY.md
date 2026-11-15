# Security

Report a suspected vulnerability through GitHub private vulnerability reporting when available, or contact the repository owner privately. Do not put tokens, database URLs with passwords, user records or exploit details in a public issue.

Use separate credentials for every deployment. Restrict exchange permissions and network access. Operational data API routes require `X-Service-API-Key`; broadcast administration uses independently issued administrator keys. The default preview has no external connections or real delivery.

If a credential enters Git history, revoke it at its provider immediately. Removing a file or rewriting history does not invalidate a key. Follow GitHub's sensitive-data removal procedure for branches, tags, pull-request refs and cached views.

Before changing repository visibility, scan all published refs and review outstanding GitHub Support remediation, attachments and logs. Local copies and forks need separate cleanup.

Do not expose PostgreSQL, Redis, monitoring dashboards or the preview server as an unauthenticated public service. The preview is designed for local inspection.
