"""Token request endpoint — lets users notify admin to issue a token."""

from __future__ import annotations

import httpx
from fastapi import APIRouter
from pydantic import BaseModel

from config.settings import get_settings

router = APIRouter(prefix="/tokens", tags=["tokens"])


class TokenRequestBody(BaseModel):
    name: str
    email: str
    reason: str | None = None


@router.post("/request", status_code=202)
async def request_token(body: TokenRequestBody) -> dict:
    """Notify the admin via Discord that a token is needed.

    Admin generates a token at raybags.com/admin and sends it to the
    user through the portfolio-base chat widget.
    """
    settings = get_settings()

    if settings.discord_webhook:
        msg = (
            "**DataForge Access Token Request**\n"
            f"**Name:** {body.name}\n"
            f"**Email:** {body.email}\n"
            f"**Reason:** {body.reason or 'Not specified'}\n\n"
            "Generate a token at `raybags.com/admin` → Access Tokens → Generate,\n"
            "then send it to the user via chat."
        )
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                await client.post(settings.discord_webhook, json={"content": msg})
        except Exception:
            pass

    return {
        "status": "requested",
        "message": (
            "Request sent! The admin will reach you via chat at raybags.com "
            "with your access token shortly."
        ),
    }
