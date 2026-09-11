from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response

from alertbot import settings_store as store
from alertbot.auth import new_session_token, verify_password
from webapp.config import COOKIE_NAME, NO_CACHE_HEADERS, templates
from webapp.deps import current_phone, require_phone
from webapp.schemas import ChannelAddBody, ChannelBody, LoginBody, RegionBody, ThreatBody, ThreatKeywordBody

router = APIRouter()


@router.get("/login")
def login_page(request: Request) -> Response:
    return templates.TemplateResponse(request, "login.html", headers=NO_CACHE_HEADERS)


@router.get("/")
def dashboard(request: Request) -> Response:
    if not current_phone(request):
        return RedirectResponse("/login")
    return templates.TemplateResponse(request, "dashboard.html", headers=NO_CACHE_HEADERS)


@router.post("/api/login")
async def api_login(body: LoginBody) -> JSONResponse:
    phone = "".join(ch for ch in body.phone if ch.isdigit())

    user = store.get_user(phone)
    if not user or not verify_password(body.password, user["salt"], user["password_hash"]):
        return JSONResponse({"error": "invalid"}, status_code=401)

    token = new_session_token()
    store.create_session(token, phone)
    resp = JSONResponse({"ok": True})
    resp.set_cookie(COOKIE_NAME, token, httponly=True, samesite="lax", max_age=60 * 60 * 24 * 30)
    return resp


@router.post("/api/logout")
async def api_logout(request: Request) -> JSONResponse:
    token = request.cookies.get(COOKIE_NAME)
    if token:
        store.delete_session(token)
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(COOKIE_NAME)
    return resp


@router.get("/api/state")
async def api_state(phone: str = Depends(require_phone)) -> dict[str, Any]:
    return store.get_state()


@router.post("/api/region")
async def api_region(body: RegionBody, phone: str = Depends(require_phone)) -> dict[str, Any]:
    store.set_region_enabled(body.region, body.enabled)
    return {"ok": True}


@router.post("/api/threat")
async def api_threat(body: ThreatBody, phone: str = Depends(require_phone)) -> dict[str, Any]:
    store.set_threat_type_enabled(body.key, body.enabled)
    return {"ok": True}


@router.post("/api/threat/keyword/add")
async def api_threat_keyword_add(body: ThreatKeywordBody, phone: str = Depends(require_phone)) -> dict[str, Any]:
    store.add_threat_keyword(body.key, body.keyword)
    return {"ok": True}


@router.post("/api/threat/keyword/remove")
async def api_threat_keyword_remove(body: ThreatKeywordBody, phone: str = Depends(require_phone)) -> dict[str, Any]:
    store.remove_threat_keyword(body.key, body.keyword)
    return {"ok": True}


@router.post("/api/channel")
async def api_channel(body: ChannelBody, phone: str = Depends(require_phone)) -> dict[str, Any]:
    store.set_channel_enabled(body.key, body.enabled)
    return {"ok": True}


@router.post("/api/channels/add", response_model=None)
async def api_channels_add(body: ChannelAddBody, phone: str = Depends(require_phone)) -> JSONResponse | dict[str, Any]:
    raw = body.input.strip()
    if not raw:
        return JSONResponse({"error": "empty"}, status_code=400)
    request_id = store.add_join_request(raw)
    return {"ok": True, "request_id": request_id}


@router.get("/api/channels/requests")
async def api_channels_requests(phone: str = Depends(require_phone)) -> list[dict[str, Any]]:
    return store.get_join_requests_recent(10)
