# main.py
import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.db import init_db, ensure_admin
from app.utils import money_miles

# Routers existentes (ajusta si alguno tiene otro nombre)
from app.auth import router as auth_router
from app.clientes import router as clientes_router
from app.pagos import router as pagos_router

# Nuevo: contabilidad
from app.contabilidad import router as contabilidad_router


app = FastAPI()

# Static
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates + filtros
templates = Jinja2Templates(directory="templates")
templates.env.filters["miles"] = money_miles


@app.on_event("startup")
def startup_event():
    init_db()

    # Admin por env vars (Render -> Environment)
    admin_user = os.getenv("ADMIN_USER", "admin")
    admin_pass = os.getenv("ADMIN_PASS", "admin123")
    ensure_admin(admin_user, admin_pass)


# Routers
app.include_router(auth_router)
app.include_router(clientes_router)
app.include_router(pagos_router)
app.include_router(contabilidad_router)
