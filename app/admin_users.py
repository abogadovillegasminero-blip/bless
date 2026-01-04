from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.auth import require_admin
from app.db import get_connection
from app.security import hash_password

router = APIRouter(prefix="/admin", tags=["Admin"])
templates = Jinja2Templates(directory="templates")


def _list_users():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, username, role FROM usuarios ORDER BY id ASC")
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def _get_username_by_id(user_id: int) -> str:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT username FROM usuarios WHERE id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return row["username"] if row else ""


def _create_user(username: str, password: str, role: str) -> bool:
    username = (username or "").strip()
    role = (role or "user").strip().lower()
    if role not in ("admin", "user"):
        role = "user"

    if not username or not password:
        return False

    hashed = hash_password(password)

    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO usuarios (username, password, role) VALUES (?, ?, ?)",
            (username, hashed, role),
        )
        conn.commit()
        ok = True
    except Exception:
        ok = False
    finally:
        conn.close()

    return ok


def _set_role(user_id: int, role: str):
    role = (role or "user").strip().lower()
    if role not in ("admin", "user"):
        role = "user"

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE usuarios SET role = ? WHERE id = ?", (role, user_id))
    conn.commit()
    conn.close()


def _delete_user(user_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM usuarios WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()


def _reset_password(user_id: int, new_password: str):
    hashed = hash_password(new_password)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE usuarios SET password = ? WHERE id = ?", (hashed, user_id))
    conn.commit()
    conn.close()


@router.get("/usuarios", response_class=HTMLResponse)
def admin_usuarios(request: Request):
    admin = require_admin(request)
    if isinstance(admin, RedirectResponse):
        return admin

    ok = request.query_params.get("ok")  # "1"
    err = request.query_params.get("err")  # "1"

    users = _list_users()

    return templates.TemplateResponse(
        "admin_usuarios.html",
        {"request": request, "user": admin, "users": users, "ok": ok, "err": err},
    )


@router.post("/usuarios/crear")
def crear_usuario(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    role: str = Form("user"),
):
    admin = require_admin(request)
    if isinstance(admin, RedirectResponse):
        return admin

    ok = _create_user(username, password, role)
    return RedirectResponse("/admin/usuarios?ok=1" if ok else "/admin/usuarios?err=1", status_code=303)


@router.post("/usuarios/cambiar_rol")
def cambiar_rol(
    request: Request,
    user_id: int = Form(...),
    role: str = Form(...),
):
    admin = require_admin(request)
    if isinstance(admin, RedirectResponse):
        return admin

    # Bloqueo mínimo: no te quites admin a ti mismo
    if str(admin.get("username")) == _get_username_by_id(int(user_id)):
        if role.strip().lower() != "admin":
            return RedirectResponse("/admin/usuarios?err=1", status_code=303)

    _set_role(int(user_id), role)
    return RedirectResponse("/admin/usuarios?ok=1", status_code=303)


@router.post("/usuarios/reset_password")
def reset_password(
    request: Request,
    user_id: int = Form(...),
    new_password: str = Form(...),
):
    admin = require_admin(request)
    if isinstance(admin, RedirectResponse):
        return admin

    new_password = (new_password or "").strip()
    if len(new_password) < 4:
        return RedirectResponse("/admin/usuarios?err=1", status_code=303)

    _reset_password(int(user_id), new_password)
    return RedirectResponse("/admin/usuarios?ok=1", status_code=303)


@router.post("/usuarios/eliminar")
def eliminar_usuario(
    request: Request,
    user_id: int = Form(...),
):
    admin = require_admin(request)
    if isinstance(admin, RedirectResponse):
        return admin

    # No se elimina a sí mismo
    if str(admin.get("username")) == _get_username_by_id(int(user_id)):
        return RedirectResponse("/admin/usuarios?err=1", status_code=303)

    _delete_user(int(user_id))
    return RedirectResponse("/admin/usuarios?ok=1", status_code=303)
