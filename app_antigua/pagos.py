from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from app.auth_utils import get_current_user
from fastapi.templating import Jinja2Templates
import pandas as pd
import os

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

RUTA_PAGOS = "data/pagos.xlsx"


def leer_pagos():
    if os.path.exists(RUTA_PAGOS):
        return pd.read_excel(RUTA_PAGOS).to_dict(orient="records")
    return []


@router.get("/pagos", response_class=HTMLResponse)
def ver_pagos(request: Request, user=Depends(get_current_user)):
    pagos = leer_pagos()
    return templates.TemplateResponse(
        "pagos.html",
        {"request": request, "pagos": pagos}
    )


@router.post("/pagos")
def guardar_pago(
    documento: str = Form(...),
    fecha: str = Form(...),
    valor: float = Form(...),
    user=Depends(get_current_user)
):
    nuevo = pd.DataFrame([{
        "documento": documento,
        "fecha": fecha,
        "valor": valor
    }])

    if os.path.exists(RUTA_PAGOS):
        df = pd.read_excel(RUTA_PAGOS)
        df = pd.concat([df, nuevo], ignore_index=True)
    else:
        df = nuevo

    df.to_excel(RUTA_PAGOS, index=False)

    return RedirectResponse("/pagos", status_code=303)
