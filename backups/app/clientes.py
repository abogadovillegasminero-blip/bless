from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from app.auth import get_current_user

router = APIRouter(prefix="/clientes")

@router.get("", response_class=HTMLResponse)
def clientes(request: Request, user=Depends(get_current_user)):
    return """
    <h1>Clientes</h1>
    <p>Usuario: {}</p>
    """.format(user["user"])
