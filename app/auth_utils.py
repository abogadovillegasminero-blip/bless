from fastapi import Request
from fastapi.responses import RedirectResponse

def get_current_user(request: Request):
    user = request.cookies.get("user")
    if not user:
        return RedirectResponse("/login", status_code=302)
    return user
