from fastapi import APIRouter, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from app.auth_utils import get_current_user

router = APIRouter()

# 🔹 LOGIN (si ya lo tienes, déjalo igual)
@router.get("/login", response_class=HTMLResponse)
def login_form():
    return """
    <h2>Login</h2>
    <form method="post">
        <input type="text" name="username" placeholder="Usuario"><br><br>
        <input type="password" name="password" placeholder="Clave"><br><br>
        <button type="submit">Ingresar</button>
    </form>
    """

@router.post("/login")
def login(username: str = Form(...), password: str = Form(...)):
    if username == "admin" and password == "admin":
        return RedirectResponse("/dashboard", status_code=302)
    return RedirectResponse("/login", status_code=302)

# 🔹 DASHBOARD (ESTE ERA EL PROBLEMA)
@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(user=Depends(get_current_user)):
    return """
    <h2>Dashboard Bless</h2>

    <a href="/clientes">Clientes</a><br><br>
    <a href="/pagos">Pagos</a><br><br>
    <a href="/reportes">Reportes</a><br><br>
    <a href="/saldos">Saldos</a><br><br>
    <a href="/backup">Backup Manual</a><br><br>
    <a href="/reporte/pdf">Generar PDF</a><br><br>

    <a href="/logout">Salir</a>
    """

# 🔹 LOGOUT
@router.get("/logout")
def logout():
    return RedirectResponse("/login", status_code=302)
