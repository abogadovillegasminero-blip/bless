import os
import sqlite3
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.db import get_connection
from app.auth import require_admin
from app.security import hash_password

router = APIRouter(prefix="/admin", tags=["Admin"])

# ✅ templates dentro de app/templates (ruta segura en Render)
BASE_DIR = os.path.dirname(__file__)  # .../app
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))  # .../app/templates


def list_users():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, username, role FROM usuarios ORDER BY role DESC, username ASC")
    rows = cur.fetchall()
    conn.close()
    return [{"id": r[0], "username": r[1], "role": r[2]} for r in rows]


def count_admins():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM usuarios WHERE role = 'admin'")
    n = cur.fetchone()[0]
    conn.close()
    return int(n)


def get_user(username: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, username, role FROM usuarios WHERE username = ?", (username,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {"id": row[0], "username": row[1], "role": row[2]}


@router.get("/usuarios", response_class=HTMLResponse)
def admin_users_page(request: Request):
    user = require_admin(request)
    if isinstance(user, RedirectResponse):
        return user

    error = request.query_params.get("error")
    ok = request.query_params.get("ok")

    usuarios = list_users()
    admins_count = count_admins()

    return templates.TemplateResponse(
        "admin_users.html",
        {
            "request": request,
            "user": user,
            "usuarios": usuarios,
            "admins_count": admins_count,
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
    return RedirectResponse("/admin/usuarios?ok=created", status_code=303)


@router.post("/usuarios/cambiar_rol")
def cambiar_rol(request: Request, username: str = Form(...)):
    admin = require_admin(request)
    if isinstance(admin, RedirectResponse):
        return admin

    username = (username or "").strip()
    if not username:
        return RedirectResponse("/admin/usuarios?error=missing", status_code=303)

    # 🔒 no cambiar tu propio rol
    if username == admin.get("username"):
        return RedirectResponse("/admin/usuarios?error=self_role", status_code=303)

    target = get_user(username)
    if not target:
        return RedirectResponse("/admin/usuarios?error=notfound", status_code=303)

    current_role = target["role"]
    new_role = "admin" if current_role == "user" else "user"

    # 🔒 no degradar al último admin
    if current_role == "admin" and new_role == "user" and count_admins() <= 1:
        return RedirectResponse("/admin/usuarios?error=last_admin", status_code=303)

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE usuarios SET role = ? WHERE username = ?", (new_role, username))
    conn.commit()
    conn.close()

    return RedirectResponse("/admin/usuarios?ok=role", status_code=303)


@router.post("/usuarios/eliminar")
def eliminar_usuario(request: Request, username: str = Form(...)):
    admin = require_admin(request)
    if isinstance(admin, RedirectResponse):
        return admin

    username = (username or "").strip()
    if not username:
        return RedirectResponse("/admin/usuarios?error=missing", status_code=303)

    # 🔒 no eliminarte tú mismo
    if username == admin.get("username"):
        return RedirectResponse("/admin/usuarios?error=self_delete", status_code=303)

    target = get_user(username)
    if not target:
        return RedirectResponse("/admin/usuarios?error=notfound", status_code=303)

    # 🔒 no eliminar al último admin
    if target["role"] == "admin" and count_admins() <= 1:
        return RedirectResponse("/admin/usuarios?error=last_admin", status_code=303)

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM usuarios WHERE username = ?", (username,))
    conn.commit()
    conn.close()

    return RedirectResponse("/admin/usuarios?ok=deleted", status_code=303)
