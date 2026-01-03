from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from app.auth import require_user
import pandas as pd
import os

router = APIRouter(prefix="/reportes", tags=["Reportes"])

BASE = "data"
PAGOS = f"{BASE}/pagos.xlsx"
EXPORT = f"{BASE}/reporte_pagos.xlsx"


@router.get("/", response_class=HTMLResponse)
def ver_reportes(request: Request):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user

    if not os.path.exists(PAGOS):
        filas = "<tr><td colspan='3'>No hay pagos</td></tr>"
    else:
        df = pd.read_excel(PAGOS)

        if "valor" in df.columns and "monto" not in df.columns:
            df = df.rename(columns={"valor": "monto"})
        if "cliente" in df.columns and "cedula" not in df.columns:
            df = df.rename(columns={"cliente": "cedula"})

        filas = ""
        for _, r in df.iterrows():
            filas += f"""
            <tr>
                <td>{r.get('cedula','')}</td>
                <td>{r.get('fecha','')}</td>
                <td>{r.get('monto','')}</td>
            </tr>
            """

    return f"""
    <html>
    <head>
        <title>Reportes</title>
        <style>
            body {{ font-family: Arial; background:#f4f6f8; padding:30px; }}
            table {{ width:100%; border-collapse: collapse; background:white; }}
            th, td {{ padding:10px; border-bottom:1px solid #ddd; text-align:center; }}
            th {{ background:#2c7be5; color:white; }}
            a {{
                display:inline-block;
                margin:20px 10px 0 0;
                padding:10px 16px;
                background:#2c7be5;
                color:white;
                text-decoration:none;
                border-radius:6px;
                font-weight:bold;
            }}
        </style>
    </head>
    <body>
        <h2>📈 Reporte de Pagos</h2>

        <a href="/reportes/exportar">📤 Exportar a Excel</a>
        <a href="/">⬅ Volver</a>

        <table>
            <tr>
                <th>Cédula</th>
                <th>Fecha</th>
                <th>Monto</th>
            </tr>
            {filas}
        </table>
    </body>
    </html>
    """


@router.get("/exportar")
def exportar_excel(request: Request):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user

    if not os.path.exists(PAGOS):
        return {"error": "No hay datos"}

    df = pd.read_excel(PAGOS)

    if "valor" in df.columns and "monto" not in df.columns:
        df = df.rename(columns={"valor": "monto"})
    if "cliente" in df.columns and "cedula" not in df.columns:
        df = df.rename(columns={"cliente": "cedula"})

    df.to_excel(EXPORT, index=False)

    return FileResponse(
        EXPORT,
        filename="reporte_pagos.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
