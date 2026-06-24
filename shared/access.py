"""Token-based rate limiting via portfolio-base service-to-service API.

DataForge has no direct DB access to the app_tokens / ip_usage_logs tables —
those live in portfolio-base's own relational database (Postgres/SQLite via
SQLAlchemy/Alembic). This module forwards each access check to a
portfolio-base service endpoint instead of talking to Supabase PostgREST.

Endpoint: POST {PORTFOLIO_API_URL}/access-tokens/check
Auth:     X-Service-Key: {PORTFOLIO_ADMIN_TOKEN}
Body:     {"app_name": str, "ip": str, "token": str | null}

Responses (forwarded as-is):
  200 {"allowed": true}   → proceed
  403 {"detail": "rate_limited"} | {"detail": "invalid_token"} → block
  401 → service key mismatch (config error; fail open so prod keeps running)

Usage:
    from shared.access import dataforge_access
    @router.post("/crawl", dependencies=[Depends(dataforge_access)])
"""

from __future__ import annotations

import contextlib

from fastapi import Depends, Header, HTTPException, Request, status


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return (request.client and request.client.host) or "unknown"


class _AppAccessChecker:
    """Callable FastAPI dependency for per-app rate limiting.

    Instantiated once per app_name so it can be used as a stable key
    in test_app.dependency_overrides.
    """

    def __init__(self, app_name: str) -> None:
        self.app_name = app_name

    async def __call__(
        self,
        request: Request,
        x_app_token: str | None = Header(None, alias="X-App-Token"),
    ) -> None:
        import httpx

        from config.settings import get_settings

        settings = get_settings()
        if not settings.portfolio_api_url or not settings.portfolio_admin_token:
            return  # not configured — allow all (local dev / CI)

        base = settings.portfolio_api_url.rstrip("/")
        ip = _client_ip(request)

        try:
            async with httpx.AsyncClient(timeout=8) as client:
                resp = await client.post(
                    f"{base}/access-tokens/check",
                    json={"app_name": self.app_name, "ip": ip, "token": x_app_token},
                    headers={
                        "X-Service-Key": settings.portfolio_admin_token,
                        "Content-Type": "application/json",
                    },
                )

            if resp.status_code == 200:
                return  # allowed

            if resp.status_code in (status.HTTP_403_FORBIDDEN,):
                detail = "rate_limited"
                with contextlib.suppress(Exception):
                    detail = resp.json().get("detail", detail)
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)

            # 401 = service key misconfigured, 5xx = portfolio-base down → fail open
        except HTTPException:
            raise
        except Exception:
            return  # network / config error — fail open, don't block the user


# Module-level singleton — stable key for dependency_overrides in tests
dataforge_access = _AppAccessChecker("dataforge")


def require_app_access(app_name: str) -> Depends:
    """Return a FastAPI Depends wrapping the per-app access checker."""
    if app_name == "dataforge":
        return Depends(dataforge_access)
    return Depends(_AppAccessChecker(app_name))
