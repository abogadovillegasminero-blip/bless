from fastapi import Request
from fastapi.responses import RedirectResponse

PUBLIC_ROUTES = ["/login", "/static"]

async def auth_guard(request: Request, call_next):
    path = request.url.path

    if any(path.startswith(p) for p in PUBLIC_ROUTES):
        return await call_next(request)

    if not request.cookies.get("user"):
        return RedirectResponse("/login", status_code=302)

    return await call_next(request)
