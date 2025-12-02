# Library Management API
1. Estructura del proyecto: qué es cada cosa

Creamos un backend tipo “API profesional” organizado por módulos:

app/main.py
Punto de entrada de FastAPI. Aquí:

Se crea app = FastAPI(...)

Se registran routers: auth, branches, etc.

Se define el evento @app.on_event("startup") que crea/verifica el admin.

Se definen rutas simples (/, /health/db).

app/core/config.py
Carga configuración desde .env usando BaseSettings (DATABASE_URL, JWT_SECRET, etc.).

app/db/session.py
Configura la conexión a PostgreSQL:

engine (conexión a la base)

SessionLocal (sesiones para cada request)

Base (clase base de SQLAlchemy para los modelos).

app/db/models.py
Modelos de base de datos:

User

LibraryBranch

Book

Loan

LoanStatusHistory
Estos modelos definen las tablas, columnas, relaciones, enums, etc.

alembic/
Sistema de migraciones:

alembic.ini → config básica

alembic/env.py → dice a Alembic qué Base.metadata usar y qué URL de BD

alembic/versions/...initial_schema.py → migración que crea las tablas.

app/schemas/...
Esquemas Pydantic para validar y serializar:

user.py → UserCreate, UserRead, etc.

auth.py → Token, etc.

branch.py → BranchCreate, BranchRead, etc.

app/core/security.py
Lógica de seguridad:

Hash de contraseñas (bcrypt vía passlib)

Creación de JWT (create_access_token)

Decodificar/verificar tokens.

app/api/v1/dependencies.py
Dependencias compartidas (por ahora get_db() para obtener una sesión de BD).

app/api/v1/dependencies_auth.py
Autenticación y autorización:

get_current_user → extrae usuario a partir del token

require_role(...) → asegura que el usuario tenga cierto rol (o admin).

app/api/v1/endpoints/auth.py
Endpoints de autenticación:

POST /api/v1/auth/register (crear user member)

POST /api/v1/auth/login (con OAuth2PasswordRequestForm)

Devuelve access_token.

app/api/v1/endpoints/branches.py
Endpoints de sucursales:

GET /api/v1/branches

POST /api/v1/branches

GET /api/v1/branches/{id}

PUT /api/v1/branches/{id}

DELETE /api/v1/branches/{id}
con control de permisos según rol.

app/services/init_admin.py
Crea un admin “embebido” (admin@library.local / admin123) si no existe.


📘 2. README COMPLETO PARA TU PROYECTO

Aquí tienes un README profesional listo para GitHub:

📚 LIBRARY-MANAGEMENT-API

API REST moderna para gestión de bibliotecas — FastAPI + PostgreSQL + SQLAlchemy + Alembic + JWT

🚀 Características principales

Autenticación con JWT

Tres roles:

ADMIN

LIBRARIAN

MEMBER

CRUD completo:

Usuarios

Sucursales

Libros

Préstamos

Historial de estados de préstamo

Sistema de préstamos con flujo:

REQUESTED → APPROVED → BORROWED → RETURNED / OVERDUE / LOST

Logging estructurado

Docker listo para despliegue

Tests con Pytest

🏗 Tecnologías

FastAPI

SQLAlchemy 2.0

Alembic

PostgreSQL

Pydantic v2 + pydantic-settings

Passlib (bcrypt)

python-jose (JWT)

Pytest

📂 Estructura del proyecto
library-management-api/
├── alembic/
│   ├── versions/
│   └── env.py
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/
│   │       ├── dependencies.py
│   │       └── dependencies_auth.py
│   ├── core/
│   │   ├── config.py
│   │   ├── security.py
│   └── db/
│       ├── models.py
│       └── session.py
├── tests/
├── requirements.txt
├── docker-compose.yml
├── Dockerfile
└── README.md

⚙️ Configuración del entorno
1. Crear entorno virtual
python3 -m venv venv
source venv/bin/activate

2. Instalar dependencias
pip install -r requirements.txt

🗄 Base de datos
Crear usuario y base de datos:
CREATE USER library_user WITH PASSWORD 'password123';
CREATE DATABASE library_db OWNER library_user;


Configura la URL en .env:

DATABASE_URL=postgresql+psycopg2://library_user:password123@localhost:5432/library_db
JWT_SECRET=secret123

🔧 Migraciones
Crear migración:
alembic revision --autogenerate -m "initial schema"

Aplicar migraciones:
alembic upgrade head

🔐 Autenticación
Login:
curl -X POST "http://127.0.0.1:8000/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@library.local&password=admin123"

🚀 Ejecutar servidor
uvicorn app.main:app --reload

📘 Documentación automática

Swagger:

http://127.0.0.1:8000/docs


ReDoc:

http://127.0.0.1:8000/redoc

🧪 Testing
pytest -v

🐳 Docker

Para levantar toda la infraestructura:

docker-compose up --build

✨ Estado actual

Autenticación funcionando

Migraciones funcionando

Modelos completos

Admin inicial auto-creado

Endpoints listos para continuar con CRUDse