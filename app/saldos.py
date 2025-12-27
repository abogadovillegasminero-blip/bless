from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from app.auth import get_current_user
import pandas as pd
import os

router = APIRouter(prefix="/saldos", tags=["Saldos"])

CLIENTES_XLSX = "data/clientes.xlsx"
PAGOS_XLSX = "data/pagos.xlsx"

@router.get("/", response_class=HTMLResponse)
def ver_saldos(user=Depends(get_current_user)):
    if not os.path.exists(CLIENTES_XLSX):
        return "<h3>No hay clientes registrados</h3>"

    clientes = pd.read_excel(CLIENTES_XLSX)

    if os.path.exists(PAGOS_XLSX):
        pagos = pd.read_excel(PAGOS_XLSX)
    else:
        pagos = pd.DataFrame(columns=["cedula", "valor"])

    pagos_sum = pagos.groupby("cedula", as_index=False)["valor"].sum()
    pagos_sum.rename(columns={"valor": "pagado"}, inplace=True)

    df = clientes.merge(pagos_sum, on="cedula", how="left")
    df["pagado"] = df["pagado"].fillna(0)
    df["saldo"] = df["prestamo"] - df["pagado"]

    filas = ""
    for _, r in df.iterrows():
        filas += f"""
        <tr>
            <td>{r['cedula']}</td>
            <td>{r['nombre']}</td>
            <td>${r['prestamo']:,.0f}</td>
            <td>${r['pagado']:,.0f}</td>
            <td><b>${r['saldo']:,.0f}</b></td>
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
