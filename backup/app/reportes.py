from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from app.auth_utils import get_current_user
import pandas as pd
import os

router = APIRouter()

@router.get("/reportes", response_class=HTMLResponse)
def reportes(user=Depends(get_current_user)):
    pagos = "data/pagos.xlsx"
    clientes = "data/clientes.xlsx"

    total_pagado = 0
    total_clientes = 0

    if os.path.exists(pagos):
        df_pagos = pd.read_excel(pagos)
        total_pagado = df_pagos["valor"].sum()

    if os.path.exists(clientes):
        df_clientes = pd.read_excel(clientes)
        total_clientes = len(df_clientes)

    return f"""
    <h2>Reportes</h2>
    <p>Total clientes: <b>{total_clientes}</b></p>
    <p>Total cobrado: <b>${total_pagado:,.0f}</b></p>

    <a href="/dashboard">Volver</a>
    """
