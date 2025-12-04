# Etapa 1: build (opcional, pero la dejamos lista para optimizar después)
FROM python:3.11-slim AS base

# Evita que Python genere .pyc y que haga buffering
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Directorio de trabajo dentro del contenedor
WORKDIR /app

# Instalar dependencias del sistema necesarias para psycopg2 y compilaciones
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        postgresql-client && \
    rm -rf /var/lib/apt/lists/*

# Copiar requirements primero para aprovechar la cache
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código
COPY . .

# Copiar el script para esperar a la base de datos
COPY wait-for-db.sh /usr/local/bin/wait-for-db.sh

# Puerto por defecto de Uvicorn
EXPOSE 8000

# Comando por defecto: arrancar FastAPI con Uvicorn después de esperar a la base de datos
CMD ["bash", "/usr/local/bin/wait-for-db.sh"]
