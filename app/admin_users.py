# app/admin_users.py
from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.auth import require_admin
from app.db import get_connection
from app.security import hash_password

router = APIRouter(prefix="/usuarios", tags=["usuarios"])
templates = Jinja2Templates(directory="templates")


@router.get("")
def users_page(request: Request):
    user = require_admin(request)
    if isinstance(user, RedirectResponse):
        return user

    conn = get_connection()
    conn.row_factory = __import__("sqlite3").Row
    cur = conn.cursor()
    cur.execute("SELECT id, username, role FROM usuarios ORDER BY id DESC")
    usuarios = cur.fetchall()
    conn.close()

    return templates.TemplateResponse(
        "usuarios.html",
        {"request": request, "user": user, "usuarios": usuarios},
    )


@router.post("/crear")
def crear_usuario(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    role: str = Form("user"),  # admin o user
):
    user = require_admin(request)
    if isinstance(user, RedirectResponse):
        return user

    username = username.strip()
    role = role.strip() if role else "user"

    hashed = hash_password(password)

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO usuarios (username, password, role) VALUES (?, ?, ?)",
        (username, hashed, role),
    )
    conn.commit()
    conn.close()

    return RedirectResponse("/usuarios", status_code=303)


@router.get("/eliminar/{user_id}")
def eliminar_usuario(request: Request, user_id: int):
    user = require_admin(request)
    if isinstance(user, RedirectResponse):
        return user

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM usuarios WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()

    return RedirectResponse("/usuarios", status_code=303)
