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

    # Normaliza columnas de clientes (tu app usa "monto")
    if "prestamo" in clientes.columns and "monto" not in clientes.columns:
        clientes.rename(columns={"prestamo": "monto"}, inplace=True)

    for col in ["cedula", "nombre", "monto"]:
        if col not in clientes.columns:
            clientes[col] = ""

    clientes["cedula"] = clientes["cedula"].astype(str)
    clientes["monto"] = pd.to_numeric(clientes["monto"], errors="coerce").fillna(0)

    if os.path.exists(PAGOS_XLSX):
        pagos = pd.read_excel(PAGOS_XLSX)
    else:
        pagos = pd.DataFrame(columns=["cedula", "valor"])

    # Compatibilidad por si guardaste pagos como "monto"
    if "monto" in pagos.columns and "valor" not in pagos.columns:
        pagos.rename(columns={"monto": "valor"}, inplace=True)

    for col in ["cedula", "valor"]:
        if col not in pagos.columns:
            pagos[col] = 0

    pagos["cedula"] = pagos["cedula"].astype(str)
    pagos["valor"] = pd.to_numeric(pagos["valor"], errors="coerce").fillna(0)

    pagos_sum = pagos.groupby("cedula", as_index=False)["valor"].sum()
    pagos_sum.rename(columns={"valor": "pagado"}, inplace=True)

    df = clientes.merge(pagos_sum, on="cedula", how="left")
    df["pagado"] = df["pagado"].fillna(0)
    df["saldo"] = df["monto"] - df["pagado"]

    filas = ""
    for _, r in df.iterrows():
        filas += f"""
        <tr>
            <td>{r['cedula']}</td>
            <td>{r['nombre']}</td>
            <td>${float(r['monto']):,.0f}</td>
            <td>${float(r['pagado']):,.0f}</td>
            <td><b>${float(r['saldo']):,.0f}</b></td>
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
            a {{ display:inline-block; margin:14px 0 0 5%; }}
        </style>
    </head>
    <body>
        <a href="/">⬅ Volver</a>
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
