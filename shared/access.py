"""Token-based rate limiting backed by the shared Supabase DB.

Uses Supabase PostgREST REST API so no ORM deps are required.
Tokens are created in portfolio-base admin (raybags.com/admin) and are
valid across all projects that share the same DATABASE_URL / Supabase project.

Usage:
    from shared.access import dataforge_access
    @router.post("/crawl", dependencies=[Depends(dataforge_access)])
"""

from __future__ import annotations

from datetime import UTC, datetime

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
        if not settings.supabase_url or not settings.supabase_service_key:
            return  # no Supabase configured — allow all (local dev / CI)

        base = settings.supabase_url.rstrip("/") + "/rest/v1"
        hdrs = {
            "apikey": settings.supabase_service_key,
            "Authorization": f"Bearer {settings.supabase_service_key}",
            "Content-Type": "application/json",
        }
        ip = _client_ip(request)

        try:
            async with httpx.AsyncClient(timeout=8) as client:
                resp = await client.get(
                    f"{base}/ip_usage_logs",
                    params={"ip": f"eq.{ip}", "app_name": f"eq.{self.app_name}"},
                    headers=hdrs,
                )
                usage = resp.json() if resp.is_success else []

                if not usage:
                    await client.post(
                        f"{base}/ip_usage_logs",
                        json={"ip": ip, "app_name": self.app_name},
                        headers={**hdrs, "Prefer": "return=minimal"},
                    )
                    return  # first run is free

                if not x_app_token:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="rate_limited",
                    )

                now = datetime.now(UTC).isoformat()
                resp = await client.get(
                    f"{base}/app_tokens",
                    params={
                        "token": f"eq.{x_app_token}",
                        "is_used": "eq.false",
                        "expires_at": f"gt.{now}",
                    },
                    headers=hdrs,
                )
                tokens = resp.json() if resp.is_success else []
                if not tokens:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="invalid_token",
                    )

                token_id = tokens[0]["id"]
                await client.patch(
                    f"{base}/app_tokens",
                    params={"id": f"eq.{token_id}"},
                    json={"is_used": True, "used_by_ip": ip, "used_at": now},
                    headers={**hdrs, "Prefer": "return=minimal"},
                )
        except HTTPException:
            raise
        except Exception:
            return  # network error — fail open, don't block the user


# Module-level singleton — stable key for dependency_overrides in tests
dataforge_access = _AppAccessChecker("dataforge")


def require_app_access(app_name: str) -> Depends:
    """Return a FastAPI Depends wrapping the per-app access checker."""
    if app_name == "dataforge":
        return Depends(dataforge_access)
    return Depends(_AppAccessChecker(app_name))
