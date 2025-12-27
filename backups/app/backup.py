from fastapi import APIRouter
from fastapi.responses import FileResponse
import zipfile
import os
from datetime import datetime

router = APIRouter()

DATA_DIR = "data"
BACKUP_DIR = "backups"

@router.get("/backup/manual")
def backup_manual():
    os.makedirs(BACKUP_DIR, exist_ok=True)

    fecha = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"{BACKUP_DIR}/backup_{fecha}.zip"

    with zipfile.ZipFile(backup_file, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(DATA_DIR):
            for file in files:
                path = os.path.join(root, file)
                zipf.write(path, arcname=path)

    return FileResponse(
        backup_file,
        filename=os.path.basename(backup_file),
        media_type="application/zip"
    )
