from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.auth import router as auth_router, get_current_user
from app.clientes import router as clientes_router
from app.pagos import router as pagos_router
from app.saldos import router as saldos_router
from app.reportes import router as reportes_router

# =========================
# APP
# =========================
app = FastAPI()

# =========================
# TEMPLATES
# =========================
templates = Jinja2Templates(directory="templates")

# =========================
# STATIC
# =========================
app.mount("/static", StaticFiles(directory="static"), name="static")

# =========================
# LOGIN HTML (GET)
# =========================
@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

# =========================
# ROUTERS (POST /login está aquí)
# =========================
app.include_router(auth_router)
app.include_router(clientes_router)
app.include_router(pagos_router)
app.include_router(saldos_router)
app.include_router(reportes_router)

# =========================
# HOME (PROTEGIDO)
# =========================
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
                background: #f4f6f8;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
            }}
            .menu {{
                background: white;
                padding: 30px;
                border-radius: 10px;
                width: 300px;
                text-align: center;
                box-shadow: 0 0 10px rgba(0,0,0,.1);
            }}
            a {{
                display: block;
                margin: 10px 0;
                padding: 10px;
                background: #2c7be5;
                color: white;
                text-decoration: none;
                border-radius: 6px;
            }}
            .admin {{ background: #6f42c1; }}
            .logout {{ background: #dc3545; }}
        </style>
    </head>
    <body>
        <div class="menu">
            <h2>BLESS</h2>
            <p>Usuario: <b>{user["username"]}</b></p>

            <a href="/clientes">Clientes</a>
            <a href="/pagos">Pagos</a>
            <a href="/saldos">Saldos</a>

            {"<a class='admin' href='/reportes'>Reportes</a>" if es_admin else ""}

            <a class="logout" href="/logout">Cerrar sesión</a>
        </div>
    </body>
    </html>
    """
