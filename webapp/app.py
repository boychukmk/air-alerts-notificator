from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from alertbot import settings_store as store
from alertbot.auth import new_session_token, verify_password

store.init_db()

app = FastAPI()

BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=BASE_DIR / "templates")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

COOKIE_NAME = "session"
NO_CACHE_HEADERS = {"Cache-Control": "no-store, must-revalidate", "Pragma": "no-cache"}


class LoginBody(BaseModel):
    phone: str
    password: str


class RegionBody(BaseModel):
    region: str
    enabled: bool


class ThreatBody(BaseModel):
    key: str
    enabled: bool


class ThreatKeywordBody(BaseModel):
    key: str
    keyword: str


class ChannelBody(BaseModel):
    key: str
    enabled: bool


class ChannelAddBody(BaseModel):
    input: str


def current_phone(request: Request):
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


@app.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", headers=NO_CACHE_HEADERS)


@app.get("/")
def dashboard(request: Request):
    if not current_phone(request):
        return RedirectResponse("/login")
    return templates.TemplateResponse(request, "dashboard.html", headers=NO_CACHE_HEADERS)


@app.post("/api/login")
async def api_login(body: LoginBody):
    phone = "".join(ch for ch in body.phone if ch.isdigit())

    user = store.get_user(phone)
    if not user or not verify_password(body.password, user["salt"], user["password_hash"]):
        return JSONResponse({"error": "invalid"}, status_code=401)

    token = new_session_token()
    store.create_session(token, phone)
    resp = JSONResponse({"ok": True})
    resp.set_cookie(COOKIE_NAME, token, httponly=True, samesite="lax", max_age=60 * 60 * 24 * 30)
    return resp


@app.post("/api/logout")
async def api_logout(request: Request):
    token = request.cookies.get(COOKIE_NAME)
    if token:
        store.delete_session(token)
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(COOKIE_NAME)
    return resp


@app.get("/api/state")
async def api_state(phone: str = Depends(require_phone)):
    return store.get_state()


@app.post("/api/region")
async def api_region(body: RegionBody, phone: str = Depends(require_phone)):
    store.set_region_enabled(body.region, body.enabled)
    return {"ok": True}


@app.post("/api/threat")
async def api_threat(body: ThreatBody, phone: str = Depends(require_phone)):
    store.set_threat_type_enabled(body.key, body.enabled)
    return {"ok": True}


@app.post("/api/threat/keyword/add")
async def api_threat_keyword_add(body: ThreatKeywordBody, phone: str = Depends(require_phone)):
    store.add_threat_keyword(body.key, body.keyword)
    return {"ok": True}


@app.post("/api/threat/keyword/remove")
async def api_threat_keyword_remove(body: ThreatKeywordBody, phone: str = Depends(require_phone)):
    store.remove_threat_keyword(body.key, body.keyword)
    return {"ok": True}


@app.post("/api/channel")
async def api_channel(body: ChannelBody, phone: str = Depends(require_phone)):
    store.set_channel_enabled(body.key, body.enabled)
    return {"ok": True}


@app.post("/api/channels/add")
async def api_channels_add(body: ChannelAddBody, phone: str = Depends(require_phone)):
    raw = body.input.strip()
    if not raw:
        return JSONResponse({"error": "empty"}, status_code=400)
    request_id = store.add_join_request(raw)
    return {"ok": True, "request_id": request_id}


@app.get("/api/channels/requests")
async def api_channels_requests(phone: str = Depends(require_phone)):
    return store.get_join_requests_recent(10)
