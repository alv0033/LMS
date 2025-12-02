📘 Library Management API — README
🔍 Overview

Library Management API es un sistema completo para administrar una red de bibliotecas, permitiendo gestionar:

Usuarios (ADMIN, LIBRARIAN, MEMBER)

Sucursales de biblioteca

Libros

Préstamos de libros y su historial

Autenticación vía JWT

Migraciones con Alembic

PostgreSQL como base de datos

Documentación interactiva con Swagger

Este proyecto está desarrollado usando FastAPI, SQLAlchemy 2.0, Alembic y PostgreSQL, siguiendo buenas prácticas de arquitectura, seguridad y mantenibilidad.

🧰 Tecnologías principales
Componente	Tecnología
Lenguaje	Python 3.12
Framework API	FastAPI
Base de datos	PostgreSQL
ORM	SQLAlchemy 2.0
Migraciones	Alembic
Autenticación	JWT (jsonwebtoken)
Logging	Logging estructurado
Containerización	Docker (pendiente)
📁 Estructura del Proyecto
library-management-api/
├── alembic/
│   ├── versions/           # Migraciones generadas
│   └── env.py
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/  # Rutas (auth, branches, etc.)
│   │       └── dependencies.py
│   ├── core/
│   │   ├── config.py       # Settings y variables de entorno
│   │   ├── security.py     # JWT y hashing
│   │   └── logging.py
│   ├── db/
│   │   ├── models.py       # Modelos SQLAlchemy
│   │   └── session.py      # SessionLocal y engine
│   ├── schemas/            # Pydantic schemas
│   ├── services/
│   │   └── init_admin.py   # Creación automática del admin inicial
│   └── main.py             # FastAPI App + Swagger personalizado
├── .gitignore
├── requirements.txt
├── alembic.ini
├── README.md
└── .env.example

🔐 Autenticación (JWT)

El sistema utiliza OAuth2 Password Flow:

El usuario llama POST /api/v1/auth/login con email/password.

El servidor valida credenciales.

Se genera un JWT con:

sub: ID del usuario

role: rol del usuario

Expiración configurable

Swagger obtiene y guarda el token automáticamente cuando usas "Authorize".

Swagger ahora no te pide pegar el token:
simplemente pones email + password y él lo maneja.

👤 Usuario Admin Automático

Cada vez que inicia la API:

Se ejecuta ensure_builtin_admin()

Si no existe un usuario admin, se crea:

email: admin@library.local
password: admin123   (puedes cambiarlo)
role: ADMIN


Este usuario no puede ser eliminado.

🛢️ Base de Datos & Migraciones
1. Crear todas las tablas
alembic upgrade head

2. Verificar si todo se creó bien
psql -U library_user -d library_db -c "\dt"


Debes ver tablas:

users

library_branches

books

loans

loan_status_history

alembic_version

📚 Endpoints Principales
🔑 Autenticación
POST /api/v1/auth/login


Ejemplo para Swagger:

username: admin@library.local
password: admin123

🏢 Sucursales (Branches)
Crear sucursal (ADMIN / LIBRARIAN)
POST /api/v1/branches/
Authorization: Bearer <token>

Obtener lista
GET /api/v1/branches/

🧪 Probar la API con Swagger

Inicia el servidor:

uvicorn app.main:app --reload


Abre:

http://127.0.0.1:8000/docs


Presiona Authorize

Ingresa email y password

Swagger añadirá automáticamente:

Authorization: Bearer <token>

⚙️ Variables de Entorno

Ejemplo .env.example:

DATABASE_URL=postgresql+psycopg2://library_user:password@localhost:5432/library_db
JWT_SECRET=supersecretkey
JWT_EXPIRE_MINUTES=60


No subas tu .env real al repositorio.

🚀 Cómo correr el proyecto
1. Activar entorno virtual
source venv/bin/activate

2. Instalar dependencias
pip install -r requirements.txt

3. Aplicar migraciones
alembic upgrade head

4. Ejecutar servidor
uvicorn app.main:app --reload

📥 Subir a GitHub

Desde la raíz del proyecto:

git add .
git commit -m "Initial API setup"
git push -u origin main

📌 Estado actual del proyecto

✔ Estructura completa del proyecto
✔ Modelos SQLAlchemy implementados
✔ Migraciones Alembic generadas y aplicadas
✔ Autenticación con JWT funcionando
✔ Admin inicial automático
✔ CRUD básico de branches funcionando
✔ Swagger personalizado (sin token manual)
✔ Configuración limpia de OpenAPI
✔ Base de datos PostgreSQL funcionando
✔ Errores solucionados (bcrypt, pydantic, alembic, openapi)

🔜 Siguientes pasos recomendados

CRUD de Books

CRUD de Loans + lógica de negocio

Historial de cambios de estado

Logging estructurado

Testing con Pytest

Dockerización completa

Roles y autorizaciones en todos los endpoints
