import os
from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from jose import jwt, JWTError
from datetime import datetime, timedelta

from app.db import get_connection
from app.security import verify_password, hash_password, looks_hashed

router = APIRouter()

SECRET_KEY = os.getenv("SECRET_KEY", "bless_secret_key")  # en Render ponlo como env var
ALGORITHM = "HS256"
TOKEN_HOURS = 8


# =========================
# DB helpers
# =========================
def get_user_by_username(username: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, username, password, role FROM usuarios WHERE username = ?",
        (username,)
    )
    row = cur.fetchone()
    conn.close()
# =========================
# GUARDS PARA RUTAS HTML
# =========================
def require_user(request: Request):
    """
    Úsalo dentro de endpoints HTML.
    Retorna dict user o RedirectResponse.
    """
    user = get_current_user(request)
    if isinstance(user, RedirectResponse):
        return user
    return user


def require_admin(request: Request):
    """
    Úsalo dentro de endpoints HTML solo admin.
    Retorna dict user o RedirectResponse.
    """
    user = get_current_user(request)
    if isinstance(user, RedirectResponse):
        return user

    if user.get("role") != "admin":
        return RedirectResponse("/", status_code=302)

    return user

    if not row:
        return None

    user_id, username, stored_password, role = row
    return {
        "id": user_id,
        "username": username,
        "password": stored_password,
        "role": role
    }


def upgrade_password_to_hash(user_id: int, new_hashed: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE usuarios SET password = ? WHERE id = ?", (new_hashed, user_id))
    conn.commit()
    conn.close()


def authenticate_user(username: str, plain_password: str):
    user = get_user_by_username(username)
    if not user:
        return None

    stored = user["password"]

    # Caso 1: ya está hasheada
    if looks_hashed(stored):
        if verify_password(plain_password, stored):
            return {"id": user["id"], "username": user["username"], "role": user["role"]}
        return None

    # Caso 2: legado en texto plano (compatibilidad)
    if plain_password == stored:
        new_hashed = hash_password(plain_password)
        upgrade_password_to_hash(user["id"], new_hashed)
        return {"id": user["id"], "username": user["username"], "role": user["role"]}

    return None


# =========================
# LOGIN
# =========================
@router.post("/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...)
):
    user = authenticate_user(username, password)
    if not user:
        # Puedes mostrar mensaje con querystring si quieres:
        # return RedirectResponse("/login?error=1", status_code=302)
        return RedirectResponse("/login", status_code=302)

    token = jwt.encode(
        {
            "sub": user["username"],
            "role": user["role"],
            "exp": datetime.utcnow() + timedelta(hours=TOKEN_HOURS)
        },
        SECRET_KEY,
        algorithm=ALGORITHM
    )

    response = RedirectResponse("/", status_code=302)

    # Render va en https, local normalmente http:
    secure_flag = (request.url.scheme == "https")

    response.set_cookie(
        "token",
        token,
        httponly=True,
        samesite="lax",
        secure=secure_flag,
        max_age=TOKEN_HOURS * 60 * 60
    )
    return response


# =========================
# DEPENDENCIA GLOBAL
# =========================
def get_current_user(request: Request):
    token = request.cookies.get("token")
    if not token:
        return RedirectResponse("/login", status_code=302)

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        role = payload.get("role")

        if not username:
            resp = RedirectResponse("/login", status_code=302)
            resp.delete_cookie("token")
            return resp

        # Validar que el usuario siga existiendo en BD
        db_user = get_user_by_username(username)
        if not db_user:
            resp = RedirectResponse("/login", status_code=302)
            resp.delete_cookie("token")
            return resp

        return {"username": username, "role": role}

    except JWTError:
        resp = RedirectResponse("/login", status_code=302)
        resp.delete_cookie("token")
        return resp


# =========================
# LOGOUT
# =========================
@router.get("/logout")
def logout():
    response = RedirectResponse("/login", status_code=302)
    response.delete_cookie("token")
    return response
