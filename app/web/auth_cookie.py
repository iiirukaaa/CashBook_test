from __future__ import annotations

from fastapi import Request

AUTH_COOKIE_NAME = "kakeibo_auth_user"


def get_auth_user_id(request: Request) -> int | None:
    raw = request.cookies.get(AUTH_COOKIE_NAME)
    if not raw:
        return None
    try:
        value = int(raw)
    except ValueError:
        return None
    return value if value > 0 else None
