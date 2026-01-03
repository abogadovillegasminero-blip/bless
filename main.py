from app.db import init_db
from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from app.auth import router as auth_router, get_current_user
from app.clientes import router as clientes_router
from app.pagos import router as pagos_router
from app.saldos import router as saldos_router
from app.reportes import router as reportes_router

app = FastAPI()
init_db()
# Templates
templates = Jinja2Templates(directory="templates")

# Static
app.mount("/static", StaticFiles(directory="static"), name="static")

# Login page (HTML)
@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

# Home
@app.get("/", response_class=HTMLResponse)
def home(request: Request, user=Depends(get_current_user)):
    if isinstance(user, RedirectResponse):
        return user

    es_admin = user["role"] == "admin"

    return f"""
    <html>
    <head>
        <title>Bless</title>
        <style>
            body {{
                font-family: Arial;
                background: linear-gradient(135deg, #1e3c72, #2a5298);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
            }}
            .menu {{
                background: white;
                padding: 30px;
                border-radius: 16px;
                width: 360px;
            }}
            a {{
                display: block;
                margin: 10px 0;
                padding: 12px;
                background: #2c7be5;
                color: white;
                text-align: center;
                border-radius: 8px;
                text-decoration: none;
            }}
            .admin {{ background: #6f42c1; }}
            .logout {{ background: #dc3545; }}
        </style>
    </head>
    <body>
        <div class="menu">
            <h2>💰 BLESS</h2>
            <p>Usuario: <b>{user["username"]}</b></p>

            <a href="/clientes">👥 Clientes</a>
            <a href="/pagos">💵 Pagos</a>
            <a href="/saldos">📊 Saldos</a>

            {"<a class='admin' href='/reportes'>📈 Reportes</a>" if es_admin else ""}

            <a class="logout" href="/logout">🔒 Cerrar sesión</a>
        </div>
    </body>
    </html>
    """

# Routers
app.include_router(auth_router)
app.include_router(clientes_router)
app.include_router(pagos_router)
app.include_router(saldos_router)
app.include_router(reportes_router)
