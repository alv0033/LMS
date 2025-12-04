#!/bin/bash
set -e

# Host y puerto del servicio de Postgres en Docker
DB_HOST="db"
DB_PORT="5432"

echo "Esperando a que la base de datos esté lista en $DB_HOST:$DB_PORT..."

# Espera a que la base de datos acepte conexiones
until pg_isready -h "$DB_HOST" -p "$DB_PORT"; do
  echo "Base de datos no lista todavía, reintentando..."
  sleep 2
done

echo "Base de datos lista. Ejecutando migraciones de Alembic..."

# Ejecutar migraciones
alembic upgrade head

echo "Migraciones aplicadas correctamente. Iniciando Uvicorn..."

# Arranca la aplicación FastAPI
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
