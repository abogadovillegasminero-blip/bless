from fastapi import FastAPI, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from app.backup import hacer_backup

from app.auth import get_current_user
from app.clientes import router as clientes_router
from app.pagos import router as pagos_router
from app.saldos import router as saldos_router
from app.reportes import router as reportes_router
from app.dashboard import router as dashboard_router

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Static
app.mount("/static", StaticFiles(directory="static"), name="static")

# Routers
app.include_router(clientes_router)
app.include_router(pagos_router)
app.include_router(saldos_router)
app.include_router(reportes_router)
app.include_router(dashboard_router)

@app.get("/", response_class=HTMLResponse)
def home(user=Depends(get_current_user)):
    rol = user.get("rol")

    html = """
    <html>
    <head>
        <link rel="stylesheet" href="/static/style.css">
    </head>
    <body>
        <div class="box">
            <h2>📌 Sistema Bless</h2>
            <ul>
    """

    if rol == "admin":
        html += """
            <li><a href="/clientes">👥 Clientes</a></li>
            <li><a href="/pagos">💵 Pagos</a></li>
            <li><a href="/saldos">📊 Saldos</a></li>
            <li><a href="/reportes">📈 Reportes</a></li>
        """
    else:
        html += """
            <li><a href="/pagos">💵 Pagos</a></li>
            <li><a href="/saldos">📊 Saldos</a></li>
        """

    html += """
            </ul>
            <a href="/logout">🔒 Cerrar sesión</a>
        </div>
    </body>
    </html>
    """

    return html
hacer_backup()
