from fastapi import APIRouter
from fastapi.responses import FileResponse
import zipfile
import os
from datetime import datetime

router = APIRouter()

@router.get("/backup")
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
