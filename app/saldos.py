from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from app.auth import require_user
import pandas as pd
import os

router = APIRouter(prefix="/saldos", tags=["Saldos"])

CLIENTES_XLSX = "data/clientes.xlsx"
PAGOS_XLSX = "data/pagos.xlsx"

@router.get("/", response_class=HTMLResponse)
def ver_saldos(request: Request):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user

    if not os.path.exists(CLIENTES_XLSX):
        return "<h3>No hay clientes registrados</h3>"

    clientes = pd.read_excel(CLIENTES_XLSX)

    if os.path.exists(PAGOS_XLSX):
        pagos = pd.read_excel(PAGOS_XLSX)
    else:
        pagos = pd.DataFrame(columns=["cedula", "monto"])

    # Asegurar columnas esperadas
    if "monto" not in pagos.columns:
        pagos["monto"] = 0

    pagos_sum = pagos.groupby("cedula", as_index=False)["monto"].sum()
    pagos_sum.rename(columns={"monto": "pagado"}, inplace=True)

    # Compatibilidad por si en clientes el campo se llama distinto
    # En tu saldos original usabas "prestamo". Si tu excel es "monto", lo mapeamos.
    if "prestamo" not in clientes.columns and "monto" in clientes.columns:
        clientes = clientes.rename(columns={"monto": "prestamo"})

    df = clientes.merge(pagos_sum, on="cedula", how="left")
    df["pagado"] = df["pagado"].fillna(0)

    if "prestamo" not in df.columns:
        return "<h3>Error: en clientes.xlsx falta la columna 'prestamo' (o 'monto')</h3>"

    df["saldo"] = df["prestamo"] - df["pagado"]

    filas = ""
    for _, r in df.iterrows():
        filas += f"""
        <tr>
            <td>{r.get('cedula','')}</td>
            <td>{r.get('nombre','')}</td>
            <td>${float(r.get('prestamo',0)):,.0f}</td>
            <td>${float(r.get('pagado',0)):,.0f}</td>
            <td><b>${float(r.get('saldo',0)):,.0f}</b></td>
        </tr>
        """

    return f"""
    <html>
    <head>
        <title>Saldos</title>
        <style>
            body {{ font-family: Arial; background:#f5f6fa; }}
            table {{ width:90%; margin:auto; border-collapse:collapse; background:white; }}
            th, td {{ padding:10px; border-bottom:1px solid #ddd; text-align:center; }}
            th {{ background:#222; color:white; }}
            h2 {{ text-align:center; }}
        </style>
    </head>
    <body>
        <h2>📊 Saldos por Cliente</h2>
        <table>
            <tr>
                <th>Cédula</th>
                <th>Nombre</th>
                <th>Préstamo</th>
                <th>Pagado</th>
                <th>Saldo</th>
            </tr>
            {filas}
        </table>
    </body>
    </html>
    """
