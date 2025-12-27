from fastapi import Request
from fastapi.responses import RedirectResponse

def require_login(request: Request):
    if not request.cookies.get("user"):
        raise RedirectResponse("/login", status_code=302)

def require_admin(request: Request):
    if request.cookies.get("role") != "admin":
        raise RedirectResponse("/clientes", status_code=302)
