import os
from datetime import datetime, timedelta

from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from jose import jwt, JWTError

from app.db import get_connection
from app.security import verify_password, hash_password, looks_hashed

router = APIRouter()

SECRET_KEY = os.getenv("SECRET_KEY", "bless_secret_key")
ALGORITHM = "HS256"
TOKEN_HOURS = 8


def get_user_by_username(username: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, username, password, role FROM usuarios WHERE username = ?",
        (username,)
    )
    row = cur.fetchone()
    conn.close()

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

    if looks_hashed(stored):
        if verify_password(plain_password, stored):
            return {"id": user["id"], "username": user["username"], "role": user["role"]}
        return None

    if plain_password == stored:
        new_hashed = hash_password(plain_password)
        upgrade_password_to_hash(user["id"], new_hashed)
        return {"id": user["id"], "username": user["username"], "role": user["role"]}

    return None


@router.post("/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...)
):
    user = authenticate_user(username, password)
    if not user:
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
    secure_flag = (request.url.scheme == "https")

    response.set_cookie(
        key="token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=secure_flag,
        max_age=TOKEN_HOURS * 60 * 60,
        path="/",
    )
    return response


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
            resp.delete_cookie("token", path="/")
            return resp

        db_user = get_user_by_username(username)
        if not db_user:
            resp = RedirectResponse("/login", status_code=302)
            resp.delete_cookie("token", path="/")
            return resp

        return {"username": username, "role": role}

    except JWTError:
        resp = RedirectResponse("/login", status_code=302)
        resp.delete_cookie("token", path="/")
        return resp


def require_user(request: Request):
    user = get_current_user(request)
    if isinstance(user, RedirectResponse):
        return user
    return user


def require_admin(request: Request):
    user = get_current_user(request)
    if isinstance(user, RedirectResponse):
        return user

    if user.get("role") != "admin":
        return RedirectResponse("/", status_code=302)

    return user


@router.get("/logout")
def logout():
    response = RedirectResponse("/login", status_code=302)
    response.delete_cookie("token", path="/")
    return response
