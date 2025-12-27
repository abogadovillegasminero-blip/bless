from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
import pandas as pd
import os
from app.auth import get_current_user

router = APIRouter(prefix="/graficos")

CLIENTES_FILE = "clientes.xlsx"

@router.get("/resumen", response_class=HTMLResponse)
def resumen(user=Depends(get_current_user)):

    if not os.path.exists(CLIENTES_FILE):
        total = al_dia = en_mora = 0
    else:
        df = pd.read_excel(CLIENTES_FILE)
        total = len(df)
        al_dia = len(df[df["saldo"] == 0])
        en_mora = len(df[df["saldo"] > 0])

    return f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Gráficos</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light">

<div class="container mt-4">

    <h3 class="mb-3">📊 Resumen General</h3>

    <!-- BOTONES EXPORTAR -->
    <div class="mb-4">
        <a href="/exportar/excel" class="btn btn-success me-2">⬇ Excel</a>
        <a href="/exportar/pdf" class="btn btn-danger">⬇ PDF</a>
    </div>

    <div class="row">

        <div class="col-md-4">
            <div class="card text-center shadow">
                <div class="card-body">
                    <h5>Total Clientes</h5>
                    <h2>{total}</h2>
                </div>
            </div>
        </div>

        <div class="col-md-4">
            <div class="card text-center shadow text-success">
                <div class="card-body">
                    <h5>Al Día</h5>
                    <h2>{al_dia}</h2>
                </div>
            </div>
        </div>

        <div class="col-md-4">
            <div class="card text-center shadow text-danger">
                <div class="card-body">
                    <h5>En Mora</h5>
                    <h2>{en_mora}</h2>
                </div>
            </div>
        </div>

    </div>

</div>
</body>
</html>
"""
