from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from app.db import init_db
from app.auth import router as auth_router, get_current_user
from app.clientes import router as clientes_router
from app.pagos import router as pagos_router
from app.saldos import router as saldos_router
from app.reportes import router as reportes_router

app = FastAPI()

# ✅ Inicializa BD al arrancar
@app.on_event("startup")
def startup_event():
    init_db()

templates = Jinja2Templates(directory="templates")

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

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
                font-family: 'Segoe UI', Arial, sans-serif;
                background: linear-gradient(135deg, #1e3c72, #2a5298);
                min-height: 100vh;
                margin: 0;
                display: flex;
                align-items: center;
                justify-content: center;
            }}
            .menu {{
                width: 360px;
                background: #ffffff;
                padding: 25px;
                border-radius: 16px;
                box-shadow: 0 20px 40px rgba(0,0,0,0.2);
            }}
            h2 {{
                text-align: center;
                margin-bottom: 20px;
                color: #1e3c72;
            }}
            .user {{
                text-align: center;
                font-size: 14px;
                color: #555;
                margin-bottom: 20px;
            }}
            a {{
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 14px;
                margin: 10px 0;
                text-decoration: none;
                background: #2c7be5;
                color: white;
                border-radius: 10px;
                font-weight: 600;
                transition: all 0.2s ease;
            }}
            a:hover {{
                background: #1a5dc9;
                transform: translateY(-2px);
            }}
            .admin {{
                background: #6f42c1;
            }}
            .admin:hover {{
                background: #59339d;
            }}
            .logout {{
                background: #dc3545;
            }}
            .logout:hover {{
                background: #b02a37;
            }}
        </style>
    </head>
    <body>
        <div class="menu">
            <h2>💰 BLESS</h2>
            <div class="user">Usuario: <b>{user["username"]}</b></div>

            <a href="/clientes">👥 Clientes</a>
            <a href="/pagos">💵 Pagos</a>
            <a href="/saldos">📊 Saldos</a>

            {"<a class='admin' href='/reportes'>📈 Reportes</a>" if es_admin else ""}

            <a class="logout" href="/logout">🔒 Cerrar sesión</a>
        </div>
    </body>
    </html>
    """

app.include_router(auth_router)
app.include_router(clientes_router)
app.include_router(pagos_router)
app.include_router(saldos_router)
app.include_router(reportes_router)
