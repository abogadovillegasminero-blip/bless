import os
import sqlite3
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.db import get_connection
from app.auth import require_admin
from app.security import hash_password

router = APIRouter(prefix="/admin", tags=["Admin"])

# ✅ apunte robusto al folder app/templates (sin importar desde dónde arranque uvicorn)
BASE_DIR = os.path.dirname(__file__)  # .../app
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))  # .../app/templates


def list_users():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT username, role FROM usuarios ORDER BY role DESC, username ASC")
    rows = cur.fetchall()
    conn.close()
    return [{"username": r[0], "role": r[1]} for r in rows]


@router.get("/usuarios", response_class=HTMLResponse)
def admin_users_page(request: Request):
    user = require_admin(request)
    if isinstance(user, RedirectResponse):
        return user

    error = request.query_params.get("error")
    ok = request.query_params.get("ok")
    usuarios = list_users()

    return templates.TemplateResponse(
        "admin_users.html",
        {
            "request": request,
            "user": user,
            "usuarios": usuarios,
            "error": error,
            "ok": ok,
        },
    )


@router.post("/usuarios/crear")
def crear_usuario(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
):
    user = require_admin(request)
    if isinstance(user, RedirectResponse):
        return user

    username = (username or "").strip()
    role = (role or "").strip().lower()

    if not username or not password:
        return RedirectResponse("/admin/usuarios?error=missing", status_code=303)

    if role not in ("admin", "user"):
        return RedirectResponse("/admin/usuarios?error=role", status_code=303)

    hashed = hash_password(password)

    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO usuarios (username, password, role) VALUES (?, ?, ?)",
            (username, hashed, role),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return RedirectResponse("/admin/usuarios?error=exists", status_code=303)

    conn.close()
    return RedirectResponse("/admin/usuarios?ok=1", status_code=303)
