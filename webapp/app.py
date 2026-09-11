from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from alertbot import settings_store as store
from webapp.config import STATIC_DIR
from webapp.routes import router

store.init_db()

app = FastAPI()
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.include_router(router)
