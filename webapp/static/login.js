async function doLogin(){
  const phone = document.getElementById('phone').value.trim();
  const password = document.getElementById('password').value;
  const r = await fetch('/api/login', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({phone, password})});
  if (r.ok) { window.location = '/'; } else {
    document.getElementById('err').textContent = 'Невірний номер або пароль';
  }
}
document.getElementById('password').addEventListener('keydown', e => { if (e.key === 'Enter') doLogin(); });
