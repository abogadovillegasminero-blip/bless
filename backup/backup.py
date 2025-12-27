import shutil
import os
from datetime import datetime

ORIGEN = "."
DESTINO = "backups"

os.makedirs(DESTINO, exist_ok=True)

fecha = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
nombre = f"backup_{fecha}.zip"

shutil.make_archive(
    base_name=os.path.join(DESTINO, nombre.replace(".zip","")),
    format="zip",
    root_dir=ORIGEN
)

print("Backup creado:", nombre)
