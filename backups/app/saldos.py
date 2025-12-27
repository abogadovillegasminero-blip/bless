from fastapi import APIRouter
from fastapi.responses import HTMLResponse, FileResponse
import pandas as pd
import os

router = APIRouter()

DATA_PATH = "app/data"
PRESTAMOS_FILE = os.path.join(DATA_PATH, "prestamos.xlsx")
PAGOS_FILE = os.path.join(DATA_PATH, "pagos.xlsx")
SALDOS_FILE = os.path.join(DATA_PATH, "saldos.xlsx")


@router.get("/saldos", response_class=HTMLResponse)
def ver_saldos():
    if not os.path.exists(PRESTAMOS_FILE):
        return "<h3>No existe prestamos.xlsx</h3>"

    prestamos = pd.read_excel(PRESTAMOS_FILE)

    if os.path.exists(PAGOS_FILE):
        pagos = pd.read_excel(PAGOS_FILE)
    else:
        pagos = pd.DataFrame(columns=["cliente", "monto"])

    pagos_total = pagos.groupby("cliente")["monto"].sum().reset_index()
    pagos_total.rename(columns={"monto": "pagado"}, inplace=True)

    prestamos = prestamos.merge(pagos_total, on="cliente", how="left")
    prestamos["pagado"] = prestamos["pagado"].fillna(0)
    prestamos["saldo"] = prestamos["valor_prestamo"] - prestamos["pagado"]

    prestamos.to_excel(SALDOS_FILE, index=False)

    tabla = prestamos[[
        "cliente",
        "valor_prestamo",
        "pagado",
        "saldo"
    ]].to_html(index=False)

    return f"""
    <h2>Saldos de Clientes</h2>
    <a href="/saldos/descargar">📥 Descargar Excel</a>
    <br><br>
    {tabla}
    """


@router.get("/saldos/descargar")
def descargar_saldos():
    if not os.path.exists(SALDOS_FILE):
        return {"error": "Archivo no generado"}
    return FileResponse(
        SALDOS_FILE,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="saldos.xlsx"
    )
