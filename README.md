# Air Alerts Notificator

Особистий бот моніторингу Telegram-каналів на предмет ракетних/дронових загроз,
який шле push-алерти на iPhone через [ntfy](https://ntfy.sh). Слухає обрані
Telegram-канали userbot-акаунтом (Telethon), класифікує текст повідомлень
(загроза + локація одночасно, без "все чисто"/гіпотетичних формулювань) і
шле серію push-сповіщень у топік конкретного міста.

## Архітектура

```
Telegram-канали ──> monitor.py (Telethon userbot)
                       │
                       ├─ filters.py     — класифікація: threat + location keywords,
                       │                   відсіювання негацій/умовних речень
                       ├─ dedup.py       — дедуплікація по нормалізованому тексту
                       ├─ storage.py     — аудит-лог усіх подій (events.db)
                       └─ notifier.py    — серія push через ntfy.sh
                       
settings.db (SQLite) — регіони, типи загроз, канали, юзери, сесії
                       │
                       └─ webapp/app.py — FastAPI-панель керування (localnet/VPN)
```

Два незалежні процеси, обидва читають/пишуть один `settings.db`:
- **`monitor.py`** — постійно слухає канали й шле алерти.
- **`webapp/app.py`** — веб-панель, де вмикаються міста/типи загроз/канали
  (`monitor.py` перечитує налаштування раз на 5 сек, без рестарту).

## Локальний запуск

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt   # прод-залежності + pytest

cp .env.example .env   # заповнити TG_API_ID / TG_API_HASH (my.telegram.org)

python seed_settings.py               # ініціалізація settings.db + користувачів панелі
python login.py request +380...       # первинний логін Telegram-акаунта (одноразово)
python login.py confirm +380... <code> <phone_code_hash>

python monitor.py                     # моніторинг + алерти
uvicorn webapp.app:app --reload --port 8081   # веб-панель, окремий термінал
```

## Тести

```bash
pytest
```

Найважливіше покриття — `tests/test_filters.py`: регресійні кейси на реальних
повідомленнях з `events.db` (і на справжніх алертах, і на хибних спрацюваннях,
які траплялись у продакшні). Будь-яка зміна в `filters.py` має проганятись
через цей набір перед деплоєм.

## Структура репозиторію

| Файл | Призначення |
|---|---|
| `monitor.py` | Головний процес: слухає Telegram, класифікує, шле алерти |
| `filters.py` | Логіка класифікації загроза+локація, відсіювання шуму |
| `notifier.py` | Відправка push через ntfy.sh |
| `dedup.py` | Дедуплікація повідомлень у пам'яті |
| `storage.py` | Аудит-лог подій (SQLite) |
| `settings_store.py` | Стан застосунку: регіони/канали/типи загроз/юзери/сесії |
| `telegram_client.py` | Спільний фабричний метод для Telethon-клієнта (єдина сесія) |
| `webapp/app.py` | FastAPI-панель керування |
| `auth.py` | Хешування паролів (PBKDF2), сесійні токени |
| `channel_input.py`, `links.py` | Парсинг вводу каналу, побудова посилань на повідомлення |
| `login.py`, `qrlogin.py`, `resend.py`, `join_invite.py`, `list_dialogs.py` | Разові адмін-скрипти для авторизації Telegram-акаунта й ручного приєднання до каналів |
| `seed_settings.py`, `add_regions.py`, `set_password.py` | Разові скрипти адміністрування `settings.db` |
| `tests/` | pytest-набір |
| `OPERATIONS.md` | Довідка з деплою/інфраструктури (сервер, systemd, VPN) |

## Продакшн

Деплой, systemd-сервіси, VPN та ntfy — див. [OPERATIONS.md](OPERATIONS.md).
