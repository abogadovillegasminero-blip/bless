# app/admin_users.py
from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.auth import require_admin
from app.db import get_connection
from app.security import hash_password

router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory="templates")


@router.get("/usuarios")
def usuarios_page(request: Request):
    user = require_admin(request)
    if isinstance(user, RedirectResponse):
        return user

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, username, role FROM usuarios ORDER BY id DESC")
        usuarios = cur.fetchall()
    finally:
        conn.close()

    return templates.TemplateResponse(
        "admin_users.html",
        {"request": request, "user": user, "usuarios": usuarios},
    )


@router.post("/usuarios/crear")
def crear_usuario(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    role: str = Form("user"),
):
    user = require_admin(request)
    if isinstance(user, RedirectResponse):
        return user

    username = username.strip()
    role = (role or "user").strip().lower()
    if role not in ("admin", "user"):
        role = "user"

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO usuarios (username, password, role) VALUES (?, ?, ?)",
            (username, hash_password(password), role),
        )
        conn.commit()
    except Exception:
        # si username ya existe, no tumbar la app
        pass
    finally:
        conn.close()

    return RedirectResponse("/admin/usuarios", status_code=303)


@router.post("/usuarios/reset")
def reset_password(
    request: Request,
    user_id: int = Form(...),
    new_password: str = Form(...),
):
    user = require_admin(request)
    if isinstance(user, RedirectResponse):
        return user

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE usuarios SET password = ? WHERE id = ?",
            (hash_password(new_password), user_id),
        )
        conn.commit()
    finally:
        conn.close()

    return RedirectResponse("/admin/usuarios", status_code=303)


@router.post("/usuarios/eliminar")
def eliminar_usuario(
    request: Request,
    user_id: int = Form(...),
):
    user = require_admin(request)
    if isinstance(user, RedirectResponse):
        return user

    # Evita borrar admin actual por accidente (si coincide por username)
    current_username = user.get("username")

    conn = get_connection()
    try:
        cur = conn.cursor()

        # No borrar el usuario logueado
        cur.execute("SELECT username FROM usuarios WHERE id = ?", (user_id,))
        row = cur.fetchone()
        if row and row["username"] == current_username:
            return RedirectResponse("/admin/usuarios", status_code=303)

        cur.execute("DELETE FROM usuarios WHERE id = ?", (user_id,))
        conn.commit()
    finally:
        conn.close()

    return RedirectResponse("/admin/usuarios", status_code=303)
