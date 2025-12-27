from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import pandas as pd
import os

from app.auth import get_current_user

router = APIRouter()
templates = Jinja2Templates(directory="templates")

DATA_DIR = "data"
CLIENTES = f"{DATA_DIR}/clientes.xlsx"
PAGOS = f"{DATA_DIR}/pagos.xlsx"

os.makedirs(DATA_DIR, exist_ok=True)

@router.get("/pagos", response_class=HTMLResponse)
def pagos_form(request: Request, user=Depends(get_current_user)):
    clientes = []

    if os.path.exists(CLIENTES):
        df = pd.read_excel(CLIENTES)
        clientes = df.to_dict(orient="records")

    return templates.TemplateResponse(
        "pagos.html",
        {
            "request": request,
            "clientes": clientes,
            "user": user
        }
    )

@router.post("/pagos/guardar")
def guardar_pago(
    cedula: str = Form(...),
    monto: float = Form(...),
    fecha: str = Form(...),
    user=Depends(get_current_user)
):
    nuevo = {
        "cedula": cedula,
        "monto": monto,
        "fecha": fecha
    }

    if os.path.exists(PAGOS):
        df = pd.read_excel(PAGOS)
        df = pd.concat([df, pd.DataFrame([nuevo])], ignore_index=True)
    else:
        df = pd.DataFrame([nuevo])

    df.to_excel(PAGOS, index=False)

    return RedirectResponse("/pagos", status_code=303)
