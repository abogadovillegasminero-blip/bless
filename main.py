# main.py
import os

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from app.db import init_db, ensure_admin
from app.auth import router as auth_router, require_user, require_admin
from app.clientes import router as clientes_router
from app.pagos import router as pagos_router
from app.saldos import router as saldos_router
from app.reportes import router as reportes_router
from app.admin_users import router as admin_users_router

app = FastAPI()
@app.get("/healthz")
def healthz():
    return {"ok": True}
@app.on_event("startup")
def startup_event():
    init_db()
    # Crea admin si no existe; si ya existe, lo deja igual.
    ensure_admin(
        os.getenv("ADMIN_USER", "admin"),
        os.getenv("ADMIN_PASS", "admin123")
    )

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


# ✅ Render hace HEAD / para health-check
@app.head("/")
def healthcheck_head():
    return Response(status_code=200)


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    error = request.query_params.get("error")
    return templates.TemplateResponse("login.html", {"request": request, "error": error})


@app.get("/", response_class=HTMLResponse)
def root():
    return RedirectResponse("/dashboard", status_code=302)


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user
    return templates.TemplateResponse("dashboard.html", {"request": request, "user": user})


# ✅ Rutas para cualquier usuario logueado (colaborador incluido)
app.include_router(auth_router)
app.include_router(clientes_router)
app.include_router(pagos_router)
app.include_router(saldos_router)

# ✅ Rutas solo ADMIN: Reportes y Usuarios
# (Si tus routers ya validan adentro, igual lo dejamos así por seguridad)
@app.middleware("http")
async def admin_guard_middleware(request: Request, call_next):
    path = request.url.path

    if path.startswith("/reportes") or path.startswith("/usuarios"):
        user = require_admin(request)
        if isinstance(user, RedirectResponse):
            return user

    return await call_next(request)

app.include_router(reportes_router)
app.include_router(admin_users_router)
