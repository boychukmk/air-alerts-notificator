async function load(){
  try {
    await loadInner();
  } catch (err) {
    console.error('load() failed:', err);
    document.getElementById('regions').innerHTML = '<div class="empty">Помилка завантаження: ' + err.message + '</div>';
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
