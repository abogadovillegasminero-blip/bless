from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import pandas as pd
import os

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

CLIENTES_FILE = "data/clientes.xlsx"
PAGOS_FILE = "data/pagos.xlsx"

@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    total_clientes = 0
    total_pagos = 0

    if os.path.exists(CLIENTES_FILE):
        total_clientes = len(pd.read_excel(CLIENTES_FILE))

    if os.path.exists(PAGOS_FILE):
        df = pd.read_excel(PAGOS_FILE)
        total_pagos = df["valor"].sum()

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "total_clientes": total_clientes,
            "total_pagos": total_pagos
        }
    )
