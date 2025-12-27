from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.auth_utils import get_current_user
import pandas as pd
import os

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

RUTA_CLIENTES = "data/clientes.xlsxuta.xlsx"
RUTA_PAGOS = "data/pagos.xlsx"


def contar_clientes():
    if os.path.exists(RUTA_CLIENTES):
        return len(pd.read_excel(RUTA_CLIENTES))
    return 0


def total_pagos():
    if os.path.exists(RUTA_PAGOS):
        df = pd.read_excel(RUTA_PAGOS)
        return df["valor"].sum()
    return 0


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, user=Depends(get_current_user)):
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "clientes": contar_clientes(),
            "total_pagos": total_pagos()
        }
    )
