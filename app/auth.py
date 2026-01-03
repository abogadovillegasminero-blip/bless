from fastapi import Request
from fastapi.responses import RedirectResponse
from app.db import get_connection

def get_user_by_username(username: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, username, role FROM usuarios WHERE username = ?",
        (username,)
    )
    row = cur.fetchone()
    conn.close()

    if not row:
        return None

    user_id, username, role = row
    return {"id": user_id, "username": username, "role": role}


def get_current_user(request: Request):
    username = request.cookies.get("user")
    if not username:
        return RedirectResponse("/login", status_code=302)

    user = get_user_by_username(username)
    if not user:
        # cookie inválido o usuario ya no existe
        resp = RedirectResponse("/login", status_code=302)
        resp.delete_cookie("user")
        return resp

    return user


def require_admin(request: Request):
    user = get_current_user(request)
    if isinstance(user, RedirectResponse):
        return user

    if user.get("role") != "admin":
        return RedirectResponse("/login", status_code=302)  # o "/no-autorizado"
    return user
