from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from jose import jwt, JWTError
from datetime import datetime, timedelta

router = APIRouter()

SECRET_KEY = "bless_secret_key"
ALGORITHM = "HS256"

# =========================
# LOGIN
# =========================
@router.post("/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...)
):
    # DEMO SIMPLE (luego se puede mejorar)
    if username == "admin":
        role = "admin"
    else:
        role = "user"

    token = jwt.encode(
        {
            "sub": username,
            "role": role,
            "exp": datetime.utcnow() + timedelta(hours=8)
        },
        SECRET_KEY,
        algorithm=ALGORITHM
    )

    response = RedirectResponse("/", status_code=302)
    response.set_cookie("token", token, httponly=True)
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
        return {
            "username": payload.get("sub"),
            "role": payload.get("role")
        }
    except JWTError:
        return RedirectResponse("/login", status_code=302)


# =========================
# LOGOUT
# =========================
@router.get("/logout")
def logout():
    response = RedirectResponse("/login", status_code=302)
    response.delete_cookie("token")
    return response
