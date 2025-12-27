from fastapi import APIRouter, Form
from fastapi.responses import HTMLResponse, RedirectResponse

router = APIRouter()

@router.get("/login", response_class=HTMLResponse)
def login_form():
    return """
    <form method="post">
        <input name="username" placeholder="Usuario">
        <input name="password" type="password" placeholder="Clave">
        <button>Ingresar</button>
    </form>
    """

@router.post("/login")
def login(username: str = Form(...), password: str = Form(...)):
    if (username == "admin" and password == "admin") or (username == "cobrador" and password == "1234"):
        response = RedirectResponse("/", status_code=302)
        response.set_cookie("user", username)
        return response
    return HTMLResponse("Credenciales incorrectas", status_code=401)
