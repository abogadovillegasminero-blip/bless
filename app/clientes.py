import os
import pandas as pd
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.auth import require_user

router = APIRouter()
templates = Jinja2Templates(directory="templates")

DATA_DIR = "data"
ARCHIVO = f"{DATA_DIR}/clientes.xlsx"

os.makedirs(DATA_DIR, exist_ok=True)


@router.get("/clientes", response_class=HTMLResponse)
def ver_clientes(request: Request):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user

    if os.path.exists(ARCHIVO):
        df = pd.read_excel(ARCHIVO)
        clientes = df.to_dict(orient="records")
    else:
        clientes = []

    return templates.TemplateResponse(
        "clientes.html",
        {"request": request, "clientes": clientes, "user": user}
    )


@router.post("/clientes/guardar")
def guardar_cliente(
    request: Request,
    nombre: str = Form(...),
    cedula: str = Form(...),
    telefono: str = Form(...),
    monto: float = Form(...),
    tipo_cobro: str = Form(...),
):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user

    nuevo = {
        "nombre": nombre,
        "cedula": cedula,
        "telefono": telefono,
        "monto": monto,
        "tipo_cobro": tipo_cobro
    }

    if os.path.exists(ARCHIVO):
        df = pd.read_excel(ARCHIVO)
        df = pd.concat([df, pd.DataFrame([nuevo])], ignore_index=True)
    else:
        df = pd.DataFrame([nuevo])

    df.to_excel(ARCHIVO, index=False)
    return RedirectResponse("/clientes", status_code=303)
