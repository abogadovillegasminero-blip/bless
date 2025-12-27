import os
import shutil
from datetime import datetime

DATA_DIR = "data"
BACKUP_DIR = "backup"

def hacer_backup():
    if not os.path.exists(DATA_DIR):
        return

    os.makedirs(BACKUP_DIR, exist_ok=True)

    fecha = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    nombre = f"backup_{fecha}.zip"
    ruta = os.path.join(BACKUP_DIR, nombre)

    shutil.make_archive(ruta.replace(".zip", ""), "zip", DATA_DIR)
