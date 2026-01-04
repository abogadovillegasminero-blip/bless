FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencias del sistema (mínimas)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
  && rm -rf /var/lib/apt/lists/*

# Instala dependencias Python
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copia el proyecto
COPY . /app

# Fly expone el puerto 8080 por defecto
ENV PORT=8080

# Ajusta el módulo si tu app está en main.py (como lo has mostrado)
CMD ["bash", "-lc", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
