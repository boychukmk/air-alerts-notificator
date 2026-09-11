from fastapi import HTTPException, Request

from alertbot import settings_store as store
from webapp.config import COOKIE_NAME


def current_phone(request: Request) -> str | None:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    session = store.get_session(token)
    if not session:
        return None
    return session["phone"]


def require_phone(request: Request) -> str:
    phone = current_phone(request)
    if not phone:
        raise HTTPException(status_code=401, detail="unauthorized")
    return phone
