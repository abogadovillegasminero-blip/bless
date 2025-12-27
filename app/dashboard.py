from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from app.auth import get_current_user
import pandas as pd
import os

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

BASE = "data"
CLIENTES = f"{BASE}/clientes.xlsx"
PAGOS = f"{BASE}/pagos.xlsx"

@router.get("/", response_class=HTMLResponse)
def dashboard(user=Depends(get_current_user)):
    if not os.path.exists(CLIENTES):
        total_clientes = 0
    else:
        total_clientes = len(pd.read_excel(CLIENTES))

    if not os.path.exists(PAGOS):
        total_pagos = 0
        total_recaudo = 0
    else:
        df = pd.read_excel(PAGOS)
        total_pagos = len(df)
        total_recaudo = df["valor"].sum()

    return f"""
    <html>
    <head>
        <title>Dashboard</title>
        <style>
            body {{
                font-family: Arial;
                background: #f4f6f8;
                padding: 40px;
            }}
            .grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
                gap: 20px;
            }}
            .card {{
                background: white;
                padding: 20px;
                border-radius: 14px;
                box-shadow: 0 10px 25px rgba(0,0,0,0.1);
                text-align: center;
            }}
            h2 {{
                margin-bottom: 10px;
                color: #1e3c72;
            }}
            .num {{
                font-size: 28px;
                font-weight: bold;
                color: #2c7be5;
            }}
            a {{
                display:block;
                margin-top:30px;
                text-align:center;
                text-decoration:none;
                color:#2c7be5;
                font-weight:bold;
            }}
        </style>
    </head>
    <body>
        <h2>📊 Dashboard General</h2>

        <div class="grid">
            <div class="card">
                <div class="num">{total_clientes}</div>
                Clientes registrados
            </div>
            <div class="card">
                <div class="num">{total_pagos}</div>
                Pagos realizados
            </div>
            <div class="card">
                <div class="num">$ {total_recaudo:,.0f}</div>
                Total recaudado
            </div>
        </div>

        <a href="/">⬅ Volver al menú</a>
    </body>
    </html>
    """
