from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import pandas as pd
import os

from app.auth import get_current_user

router = APIRouter()
templates = Jinja2Templates(directory="templates")

DATA_DIR = "data"
ARCHIVO = f"{DATA_DIR}/clientes.xlsx"

os.makedirs(DATA_DIR, exist_ok=True)

@router.get("/clientes", response_class=HTMLResponse)
def ver_clientes(request: Request, user=Depends(get_current_user)):
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
    nombre: str = Form(...),
    cedula: str = Form(...),
    telefono: str = Form(...),
    monto: float = Form(...),
    tipo_cobro: str = Form(...),  # ⚠️ ESTE NAME ES OBLIGATORIO
    user=Depends(get_current_user)
):
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
