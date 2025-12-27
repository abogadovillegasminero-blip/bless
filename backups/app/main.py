from app.dashboard import router as dashboard_router
from fastapi import FastAPI
from fastapi.responses import FileResponse
import zipfile
import os
from datetime import datetime
from app.graficos import router as graficos_router

from app.saldos import router as saldos_router
from app.auth import router as auth_router
from app.clientes import router as clientes_router
from app.pagos import router as pagos_router
from app.reportes import router as reportes_router
from app.saldos import router as saldos_router
from app.dashboard import router as dashboard_router

app = FastAPI()

# REGISTRO DE ROUTERS
app.include_router(auth_router)
app.include_router(clientes_router)
app.include_router(pagos_router)
app.include_router(reportes_router)
app.include_router(saldos_router)
app.include_router(dashboard_router)
app.include_router(dashboard_router)
app.include_router(graficos_router)
app.include_router(saldos_router)

# BACKUP AUTOMÁTICO
@app.get("/backup")
def crear_backup():
    os.makedirs("backup", exist_ok=True)

    fecha = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_path = f"backup/backup_{fecha}.zip"

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for carpeta in ["app", "data"]:
            if os.path.exists(carpeta):
                for root, _, files in os.walk(carpeta):
                    for file in files:
                        ruta = os.path.join(root, file)
                        zipf.write(ruta)

    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename=os.path.basename(zip_path)
    )
from app.backup import router as backup_router
app.include_router(backup_router)