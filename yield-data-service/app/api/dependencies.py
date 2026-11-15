"""Authorization shared by data-service operational routes."""

import secrets

from fastapi import Depends, HTTPException, Request
from fastapi.security import APIKeyHeader

from app.config import settings

service_key = APIKeyHeader(name="X-Service-API-Key", auto_error=False)


async def require_service_key(key: str | None = Depends(service_key)) -> None:
    """Fail closed when a service key has not been configured."""
    if not settings.service_api_key:
        raise HTTPException(status_code=503, detail="Service authorization is not configured")
    if not key or not secrets.compare_digest(key, settings.service_api_key):
        raise HTTPException(status_code=401, detail="Invalid service API key")


async def protect_operations(request: Request, key: str | None = Depends(service_key)) -> None:
    """Public catalogue reads are open; writes and diagnostic calls are private."""
    if request.method not in {"GET", "HEAD", "OPTIONS"} or any(
        part in request.url.path for part in ("/test", "/aggregation/", "/scheduler/")
    ):
        await require_service_key(key)
