import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

import settings_store as store
from auth import verify_password, new_session_token, new_readable_password  # noqa: F401

store.init_db()

app = FastAPI()

COOKIE_NAME = "session"


def current_phone(request: Request):
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    session = store.get_session(token)
    if not session:
        return None
    return session["phone"]


LOGIN_HTML = """
<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Alert Monitor — Вхід</title>
<style>
:root{
  --bg:#0b0d10; --card:#15181d; --card-border:#22262d; --text:#eef0f2; --muted:#8a919b;
  --accent:#ff4b4b; --accent2:#ff8a3d; --ring:0 0 0 3px rgba(255,75,75,.25);
}
*{box-sizing:border-box}
body{
  margin:0; min-height:100vh; display:flex; align-items:center; justify-content:center;
  font-family:-apple-system,BlinkMacSystemFont,'SF Pro Text',sans-serif;
  background:radial-gradient(1200px 600px at 50% -10%, #201417 0%, var(--bg) 55%);
  color:var(--text); padding:24px;
}
.card{
  width:100%; max-width:360px; background:var(--card); border:1px solid var(--card-border);
  border-radius:20px; padding:32px 24px; box-shadow:0 20px 60px rgba(0,0,0,.45);
}
.badge{
  width:56px; height:56px; border-radius:16px; margin:0 auto 18px;
  background:linear-gradient(135deg, var(--accent), var(--accent2));
  display:flex; align-items:center; justify-content:center; font-size:26px;
}
h1{font-size:20px; text-align:center; margin:0 0 4px; letter-spacing:-.2px}
.sub{color:var(--muted); text-align:center; font-size:13px; margin:0 0 24px}
input{
  width:100%; padding:14px 16px; margin:6px 0; font-size:16px; color:var(--text);
  background:#0f1114; border:1px solid var(--card-border); border-radius:12px; outline:none;
}
input:focus{border-color:var(--accent); box-shadow:var(--ring)}
button{
  width:100%; padding:14px; margin-top:12px; font-size:16px; font-weight:600;
  background:linear-gradient(135deg, var(--accent), var(--accent2)); color:#fff; border:none;
  border-radius:12px; -webkit-tap-highlight-color:transparent;
}
button:active{opacity:.85}
.err{color:var(--accent); min-height:18px; font-size:13px; text-align:center; margin-top:10px}
</style></head><body>
<div class="card">
  <div class="badge">🚨</div>
  <h1>Alert Monitor</h1>
  <p class="sub">Вхід за номером телефону</p>
  <input id="phone" inputmode="numeric" placeholder="Номер телефону (380...)">
  <input id="password" type="password" inputmode="numeric" placeholder="Пароль">
  <button onclick="doLogin()">Увійти</button>
  <p class="err" id="err"></p>
</div>
<script>
async function doLogin(){
  const phone = document.getElementById('phone').value.trim();
  const password = document.getElementById('password').value;
  const r = await fetch('/api/login', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({phone, password})});
  if (r.ok) { window.location = '/'; } else {
    document.getElementById('err').textContent = 'Невірний номер або пароль';
  }
}
document.getElementById('password').addEventListener('keydown', e => { if (e.key === 'Enter') doLogin(); });
</script>
</body></html>
"""

DASHBOARD_HTML = """
<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Alert Monitor</title>
<style>
:root{
  --bg:#0b0d10; --card:#15181d; --card-border:#22262d; --text:#eef0f2; --muted:#8a919b;
  --accent:#ff4b4b; --accent2:#ff8a3d; --ok:#3ddc84;
}
*{box-sizing:border-box; -webkit-tap-highlight-color:transparent}
body{
  margin:0; font-family:-apple-system,BlinkMacSystemFont,'SF Pro Text',sans-serif;
  background:var(--bg); color:var(--text);
  padding:calc(20px + env(safe-area-inset-top)) 16px calc(40px + env(safe-area-inset-bottom));
}
.wrap{max-width:520px; margin:0 auto}
.topbar{display:flex; align-items:center; justify-content:space-between; margin-bottom:22px}
.brand{display:flex; align-items:center; gap:10px}
.brand .badge{
  width:34px; height:34px; border-radius:10px; display:flex; align-items:center; justify-content:center;
  background:linear-gradient(135deg, var(--accent), var(--accent2)); font-size:17px;
}
.brand h1{font-size:17px; margin:0; letter-spacing:-.2px}
.status{display:flex; align-items:center; gap:6px; font-size:12px; color:var(--muted)}
.dot{width:7px; height:7px; border-radius:50%; background:var(--ok); box-shadow:0 0 8px var(--ok)}
.logout{font-size:12px; color:var(--muted); text-decoration:none; padding:6px 10px; border:1px solid var(--card-border); border-radius:20px}

.section{margin-bottom:26px}
.section-title{font-size:13px; color:var(--muted); text-transform:uppercase; letter-spacing:.06em; margin:0 0 10px 4px}
.card{background:var(--card); border:1px solid var(--card-border); border-radius:16px; overflow:hidden}

select{
  width:100%; font-size:16px; padding:14px 16px; color:var(--text); background:var(--card);
  border:none; appearance:none; -webkit-appearance:none;
  background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='10' height='6'><path d='M0 0l5 6 5-6z' fill='%238a919b'/></svg>");
  background-repeat:no-repeat; background-position:right 16px center;
}

.row{
  display:flex; justify-content:space-between; align-items:center; padding:14px 16px;
  border-bottom:1px solid var(--card-border);
}
.row:last-child{border-bottom:none}
.row .label{font-size:15px}
.row .label .sub{display:block; font-size:12px; color:var(--muted); margin-top:2px}

.switch{position:relative; width:48px; height:28px; flex:none}
.switch input{opacity:0; width:0; height:0}
.slider{position:absolute; cursor:pointer; inset:0; background:#2b2f36; border-radius:28px; transition:.2s}
.slider:before{content:"";position:absolute; height:22px; width:22px; left:3px; top:3px; background:#fff; border-radius:50%; transition:.2s; box-shadow:0 1px 3px rgba(0,0,0,.3)}
input:checked + .slider{background:linear-gradient(135deg, var(--accent), var(--accent2))}
input:checked + .slider:before{transform:translateX(20px)}

.empty{padding:18px 16px; color:var(--muted); font-size:14px}

.addbox{margin-top:10px; display:flex; gap:8px; padding:10px; align-items:center}
.addbox input{
  flex:1; font-size:16px; padding:12px 14px; color:var(--text); background:#0f1114;
  border:1px solid var(--card-border); border-radius:10px; outline:none;
}
.addbox input:focus{border-color:var(--accent)}
.addbox button{
  flex:none; padding:12px 16px; font-size:14px; font-weight:600; color:#fff; border:none;
  border-radius:10px; background:linear-gradient(135deg, var(--accent), var(--accent2));
}
.hint{font-size:12px; color:var(--muted); margin:8px 4px 0}

.threat-block{border-bottom:1px solid var(--card-border)}
.threat-block:last-child{border-bottom:none}
.threat-head{display:flex; justify-content:space-between; align-items:center; padding:14px 16px; cursor:pointer}
.threat-head .label{display:flex; align-items:center; gap:6px}
.chev{color:var(--muted); font-size:11px; transition:transform .15s}
.chev.open{transform:rotate(90deg)}
.kw-panel{padding:0 16px 14px}
.kw-list{display:flex; flex-wrap:wrap; gap:6px; margin-bottom:10px}
.kw-chip{
  display:flex; align-items:center; gap:6px; background:#0f1114; border:1px solid var(--card-border);
  border-radius:20px; padding:6px 10px; font-size:13px; color:var(--text);
}
.kw-chip .x{color:var(--muted); cursor:pointer; font-size:12px}
.kw-add{display:flex; gap:8px}
.kw-add input{
  flex:1; font-size:16px; padding:10px 12px; color:var(--text); background:#0f1114;
  border:1px solid var(--card-border); border-radius:8px; outline:none;
}
.kw-add button{
  flex:none; padding:10px 14px; font-size:13px; font-weight:600; color:#fff; border:none;
  border-radius:8px; background:linear-gradient(135deg, var(--accent), var(--accent2));
}
.copyall{
  width:100%; margin-top:10px; padding:12px; font-size:14px; font-weight:600; color:var(--text);
  background:var(--card); border:1px solid var(--card-border); border-radius:12px;
}
.copyall:active{opacity:.7}
</style></head><body>
<div class="wrap">
  <div class="topbar">
    <div class="brand">
      <div class="badge">🚨</div>
      <h1>Alert Monitor</h1>
    </div>
    <div style="display:flex; align-items:center; gap:12px">
      <div class="status"><span class="dot"></span>онлайн</div>
      <a class="logout" href="#" onclick="logout()">вийти</a>
    </div>
  </div>

  <div class="section">
    <div class="section-title">Міста (можна декілька одночасно)</div>
    <div class="card" id="regions"></div>
    <button class="copyall" id="copyAllTopics" style="display:none">Скопіювати всі топіки</button>
  </div>

  <div class="section">
    <div class="section-title">Типи загроз</div>
    <div class="card" id="threats"></div>
  </div>

  <div class="section">
    <div class="section-title">Джерела (канали)</div>
    <div class="card" id="channels"></div>
    <div class="card addbox">
      <input id="channelInput" placeholder="@канал або t.me/... або t.me/+запрошення">
      <button id="addBtn" onclick="addChannel()">Додати</button>
    </div>
    <p class="hint" id="addHint"></p>
  </div>
</div>

<script>
function copyToClipboard(text, btn){
  const originalLabel = btn.textContent;
  function done(ok){
    btn.textContent = ok ? '✓ Скопійовано' : '✗ Не вдалося скопіювати';
    setTimeout(function(){ btn.textContent = originalLabel; }, 1500);
  }
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(function(){ done(true); }).catch(function(){ fallbackCopy(text, done); });
  } else {
    fallbackCopy(text, done);
  }
}
function fallbackCopy(text, done){
  try {
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.style.position = 'fixed'; ta.style.left = '-9999px';
    document.body.appendChild(ta);
    ta.focus(); ta.select();
    const ok = document.execCommand('copy');
    document.body.removeChild(ta);
    done(ok);
  } catch (e) {
    done(false);
  }
}

async function load(){
  try {
    await loadInner();
  } catch (err) {
    const msg = (err && err.message) ? err.message : String(err);
    document.getElementById('regions').innerHTML =
      '<div class="empty" style="color:#ff4b4b">Помилка: ' + msg + '</div>';
  }
}

async function loadInner(){
  const r = await fetch('/api/state', {cache: 'no-store'});
  if (r.status === 401) { window.location = '/login'; return; }
  const s = await r.json();

  const regionsDiv = document.getElementById('regions');
  regionsDiv.innerHTML = '';
  for (const [key, r] of Object.entries(s.regions)) {
    const label = r.label + (r.enabled && r.ntfy_topic ? '' : '');
    const row = toggleRow(label, r.enabled, (v) => setRegion(key, v));
    if (r.enabled && r.ntfy_topic) {
      const sub = document.createElement('span');
      sub.className = 'sub'; sub.textContent = 'топік: ' + r.ntfy_topic;
      row.querySelector('.label').appendChild(sub);
    }
    regionsDiv.appendChild(row);
  }

  const copyAllBtn = document.getElementById('copyAllTopics');
  const regionsWithTopics = Object.values(s.regions).filter(function(reg){ return reg.ntfy_topic; });
  if (regionsWithTopics.length) {
    copyAllBtn.style.display = 'block';
    copyAllBtn.onclick = function(){
      const lines = regionsWithTopics.map(function(reg){ return reg.label + ' — ' + reg.ntfy_topic; });
      copyToClipboard(lines.join('\n'), copyAllBtn);
    };
  } else {
    copyAllBtn.style.display = 'none';
  }

  const threatsDiv = document.getElementById('threats');
  threatsDiv.innerHTML = '';
  const threatEntries = Object.entries(s.threat_types);
  if (!threatEntries.length) threatsDiv.innerHTML = '<div class="empty">Немає налаштованих типів загроз</div>';
  for (const [key, t] of threatEntries) {
    threatsDiv.appendChild(threatBlock(key, t));
  }

  const chDiv = document.getElementById('channels');
  chDiv.innerHTML = '';
  if (!s.channels.length) chDiv.innerHTML = '<div class="empty">Немає підключених каналів</div>';
  for (const c of s.channels) {
    chDiv.appendChild(toggleRow(c.label, c.enabled, (v) => setChannel(c.key, v)));
  }
}

function threatBlock(key, t){
  const block = document.createElement('div'); block.className = 'threat-block';

  const head = document.createElement('div'); head.className = 'threat-head';
  const labelWrap = document.createElement('div'); labelWrap.className = 'label';
  const chev = document.createElement('span'); chev.className = 'chev'; chev.textContent = '▶';
  const labelText = document.createElement('span'); labelText.textContent = t.label;
  labelWrap.appendChild(chev); labelWrap.appendChild(labelText);

  const sw = document.createElement('label'); sw.className = 'switch';
  const input = document.createElement('input'); input.type = 'checkbox'; input.checked = t.enabled;
  input.onclick = (e) => e.stopPropagation();
  input.onchange = () => setThreat(key, input.checked);
  const slider = document.createElement('span'); slider.className = 'slider';
  sw.appendChild(input); sw.appendChild(slider);

  head.appendChild(labelWrap); head.appendChild(sw);

  const panel = document.createElement('div'); panel.className = 'kw-panel'; panel.style.display = 'none';
  renderKeywords(panel, key, t.keywords);

  head.onclick = () => {
    const open = panel.style.display !== 'none';
    panel.style.display = open ? 'none' : 'block';
    chev.classList.toggle('open', !open);
  };

  block.appendChild(head); block.appendChild(panel);
  return block;
}

function renderKeywords(panel, key, keywords){
  panel.innerHTML = '';
  const list = document.createElement('div'); list.className = 'kw-list';
  for (const kw of keywords) {
    const chip = document.createElement('span'); chip.className = 'kw-chip';
    const txt = document.createElement('span'); txt.textContent = kw;
    const x = document.createElement('span'); x.className = 'x'; x.textContent = '✕';
    x.onclick = async () => {
      await fetch('/api/threat/keyword/remove', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({key, keyword: kw})});
      const idx = keywords.indexOf(kw); if (idx > -1) keywords.splice(idx, 1);
      renderKeywords(panel, key, keywords);
    };
    chip.appendChild(txt); chip.appendChild(x);
    list.appendChild(chip);
  }
  panel.appendChild(list);

  const addRow = document.createElement('div'); addRow.className = 'kw-add';
  const inp = document.createElement('input'); inp.placeholder = 'нове слово-тригер';
  const btn = document.createElement('button'); btn.textContent = 'Додати';
  const submit = async () => {
    const val = inp.value.trim();
    if (!val) return;
    await fetch('/api/threat/keyword/add', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({key, keyword: val})});
    keywords.push(val); inp.value = '';
    renderKeywords(panel, key, keywords);
  };
  btn.onclick = submit;
  inp.addEventListener('keydown', e => { if (e.key === 'Enter') submit(); });
  addRow.appendChild(inp); addRow.appendChild(btn);
  panel.appendChild(addRow);
}

function toggleRow(label, checked, onChange){
  const row = document.createElement('div'); row.className = 'row';
  const span = document.createElement('span'); span.className = 'label'; span.textContent = label;
  const lbl = document.createElement('label'); lbl.className = 'switch';
  const input = document.createElement('input'); input.type = 'checkbox'; input.checked = checked;
  input.onchange = () => onChange(input.checked);
  const slider = document.createElement('span'); slider.className = 'slider';
  lbl.appendChild(input); lbl.appendChild(slider);
  row.appendChild(span); row.appendChild(lbl);
  return row;
}

async function setRegion(key, enabled){
  await fetch('/api/region', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({region: key, enabled})});
  load();
}
async function setThreat(key, enabled){
  await fetch('/api/threat', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({key, enabled})});
}
async function setChannel(key, enabled){
  await fetch('/api/channel', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({key, enabled})});
}
async function logout(){
  await fetch('/api/logout', {method:'POST'});
  window.location = '/login';
}

async function addChannel(){
  const input = document.getElementById('channelInput');
  const hint = document.getElementById('addHint');
  const val = input.value.trim();
  if (!val) return;

  hint.textContent = 'Додається...';
  const r = await fetch('/api/channels/add', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({input: val})});
  if (!r.ok) { hint.textContent = 'Помилка запиту'; return; }
  input.value = '';
  pollAddResult();
}

async function pollAddResult(triesLeft = 8){
  const hint = document.getElementById('addHint');
  const r = await fetch('/api/channels/requests');
  const reqs = await r.json();
  const latest = reqs[0];
  if (latest && latest.status === 'pending' && triesLeft > 0) {
    setTimeout(() => pollAddResult(triesLeft - 1), 1500);
    return;
  }
  if (latest && latest.status === 'done') {
    hint.textContent = '✓ ' + (latest.result || 'додано');
    load();
  } else if (latest && latest.status === 'failed') {
    hint.textContent = '✗ ' + (latest.result || 'не вдалося додати');
  } else {
    hint.textContent = '';
  }
}

document.getElementById('channelInput').addEventListener('keydown', e => { if (e.key === 'Enter') addChannel(); });

load();
</script>
</body></html>
"""


NO_CACHE_HEADERS = {"Cache-Control": "no-store, must-revalidate", "Pragma": "no-cache"}


@app.get("/login", response_class=HTMLResponse)
def login_page():
    return HTMLResponse(LOGIN_HTML, headers=NO_CACHE_HEADERS)


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    if not current_phone(request):
        return RedirectResponse("/login")
    return HTMLResponse(DASHBOARD_HTML, headers=NO_CACHE_HEADERS)


@app.post("/api/login")
async def api_login(request: Request, response: Response):
    body = await request.json()
    phone = "".join(ch for ch in body.get("phone", "") if ch.isdigit())
    password = body.get("password", "")

    user = store.get_user(phone)
    if not user or not verify_password(password, user["salt"], user["password_hash"]):
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


def _require_auth(request: Request):
    phone = current_phone(request)
    if not phone:
        return None
    return phone


@app.get("/api/state")
async def api_state(request: Request):
    if not _require_auth(request):
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    return store.get_state()


@app.post("/api/region")
async def api_region(request: Request):
    if not _require_auth(request):
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    body = await request.json()
    store.set_region_enabled(body["region"], body["enabled"])
    return {"ok": True}


@app.post("/api/threat")
async def api_threat(request: Request):
    if not _require_auth(request):
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    body = await request.json()
    store.set_threat_type_enabled(body["key"], body["enabled"])
    return {"ok": True}


@app.post("/api/threat/keyword/add")
async def api_threat_keyword_add(request: Request):
    if not _require_auth(request):
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    body = await request.json()
    store.add_threat_keyword(body["key"], body["keyword"])
    return {"ok": True}


@app.post("/api/threat/keyword/remove")
async def api_threat_keyword_remove(request: Request):
    if not _require_auth(request):
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    body = await request.json()
    store.remove_threat_keyword(body["key"], body["keyword"])
    return {"ok": True}


@app.post("/api/channel")
async def api_channel(request: Request):
    if not _require_auth(request):
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    body = await request.json()
    store.set_channel_enabled(body["key"], body["enabled"])
    return {"ok": True}


@app.post("/api/channels/add")
async def api_channels_add(request: Request):
    if not _require_auth(request):
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    body = await request.json()
    raw = (body.get("input") or "").strip()
    if not raw:
        return JSONResponse({"error": "empty"}, status_code=400)
    request_id = store.add_join_request(raw)
    return {"ok": True, "request_id": request_id}


@app.get("/api/channels/requests")
async def api_channels_requests(request: Request):
    if not _require_auth(request):
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    return store.get_join_requests_recent(10)
