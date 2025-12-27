from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from app.auth_utils import get_current_user
import pandas as pd
import os

router = APIRouter()

@router.get("/saldos", response_class=HTMLResponse)
def saldos(user=Depends(get_current_user)):
    clientes = "data/clientes.xlsx"
    pagos = "data/pagos.xlsx"

    saldo = 0

    if os.path.exists(clientes):
        df_clientes = pd.read_excel(clientes)
        saldo += df_clientes["valor_prestamo"].sum()

    if os.path.exists(pagos):
        df_pagos = pd.read_excel(pagos)
        saldo -= df_pagos["valor"].sum()

    return f"""
    <h2>Saldos</h2>
    <p>Saldo total pendiente: <b>${saldo:,.0f}</b></p>

    <a href="/dashboard">Volver</a>
    """
