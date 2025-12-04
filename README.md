📚 Library Management System API
API profesional desarrollada en FastAPI, diseñada para gestionar un sistema completo de biblioteca con múltiples sucursales, préstamos de libros, autenticación JWT, control de acceso basado en roles, logging estructurado y un suite de testing funcional completo.

Este proyecto implementa todas las prácticas modernas de desarrollo backend, con arquitectura limpia, validaciones fuertes, documentación clara y un enfoque enterprise-grade.

🚀 Características principales
Autenticación segura con JWT
CRUD completo para:
Usuarios (Admin)
Sucursales
Libros
Préstamos
Reglas de negocio avanzadas:
Máximo 5 préstamos activos por usuario
Flujo de préstamos con estados (REQUESTED → APPROVED → BORROWED → RETURNED)
Transiciones controladas por rol (Member, Librarian, Admin)
Job automático para marcar préstamos como OVERDUE
Logging estructurado JSON compatible con ELK/Datadog/Splunk
Filtros avanzados: búsqueda por título, autor, ISBN, sucursal
Ordenamiento dinámico: asc/desc por cualquier campo permitido
Paginación completa
Manejo de errores profesional
Testing con Pytest: unit, integration, functional
Docker & Docker Compose
## 🧱 Arquitectura del Proyecto


library-management-api/
├── alembic/
│   ├── env.py
│   ├── versions/           # Migraciones Alembic
│   ├── README
│   └── script.py.mako
│
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/  # Rutas (auth, users, branches, books, loans, stats, etc.)
│   │       └── dependencies.py / dependencies_auth.py
│   │
│   ├── core/
│   │   ├── config.py       # Configuración (settings, .env)
│   │   ├── logging.py      # Configuración de logging estructurado
│   │   └── security.py     # JWT, hashing de contraseñas, utilidades de seguridad
│   │
│   ├── db/
│   │   ├── __init__.py
│   │   ├── models.py       # Modelos SQLAlchemy (User, LibraryBranch, Book, Loan, etc.)
│   │   └── session.py      # SessionLocal, engine, Base
│   │
│   ├── schemas/            # Esquemas Pydantic (request/response)
│   ├── services/           # Lógica de negocio (ej. loans, init_admin, jobs)
│   ├── __init__.py
│   └── main.py             # Instancia FastAPI, middlewares, registro de routers
│
├── tests/
│   ├── unit/               # Tests unitarios (lógica pura)
│   ├── integration/        # Tests de integración (DB, servicios)
│   ├── functional/         # Tests funcionales end-to-end con TestClient
│   └── conftest.py         # Fixtures compartidas (client, db, users, tokens, etc.)
│
├── .env                    # Config local (no se commitea)
├── .env.docker             # Config para entorno Docker (no usado)
├── .env.example            # Plantilla de variables de entorno
├── alembic.ini             # Config Alembic
├── docker-compose.yml      # Servicios: API + PostgreSQL (+ PgAdmin opcional)
├── Dockerfile              # Imagen de la API (FastAPI + Uvicorn)
├── pytest.ini              # Configuración Pytest
├── requirements.txt        # Dependencias del proyecto
├── wait-for-db.sh          # Script para esperar la DB en Docker
└── main.py                 # Punto de entrada para `uvicorn main:app` en entorno root

🧩 Modelos y Reglas de Negocio
👤 Usuarios
Roles soportados:

Rol	Permisos
MEMBER	Pedir préstamos, ver libros/sucursales
LIBRARIAN	Crear libros, aprobar préstamos
ADMIN	Control total, gestionar usuarios
📚 Libros
Reglas:

ISBN es único
Si se intenta crear un libro con ISBN ya existente:
No se crea uno nuevo
Se devuelve el existente (código 200/201 según lógica del proyecto)
available_copies siempre ≤ total_copies
🔄 Préstamos
Estados:

REQUESTED → APPROVED → BORROWED → RETURNED ↘ LOST BORROWED → OVERDUE (job automático)

Reglas:

Un usuario puede tener máximo 5 préstamos activos
Member solo puede cancelar mientras está en REQUESTED
Librarian maneja flujos operativos
Admin puede forzar cambios
🔐 Autenticación
Autenticación vía JWT Bearer Token.

POST /api/v1/auth/login Authorization: Bearer

🧪 Testing
El proyecto incluye:

✔ Unit tests
✔ Integration tests
✔ Functional tests completos
✔ Validación de logging
✔ Validación de reglas de negocio
✔ Validación de flujo de préstamos
Ejecutar pruebas:

pytest -q

📝 Logging estructurado
Todos los logs están en formato JSON.

Ejemplo:

{
  "timestamp": "2025-12-02T23:54:51Z",
  "level": "INFO",
  "logger": "api.loans",
  "operation": "loan_status_change",
  "loan_id": 12,
  "old_status": "REQUESTED",
  "new_status": "APPROVED",
  "user_id": 3,
  "request_id": "b1f32..."
}

🗄️ Base de Datos

Motor recomendado: PostgreSQL 15+

Migraciones:

alembic upgrade head

⚙️ Variables de entorno

Crear un archivo .env:

DATABASE_URL=postgresql+psycopg2://postgres:postgres@db:5432/library
JWT_SECRET=supersecret123
LOG_LEVEL=60

ADMIN_EMAIL=admin@library.local
ADMIN_PASSWORD=admin123

🐳 Docker

Levantar todo:

docker compose up --build


Servicios:

Servicio	Puerto
API FastAPI	8000
PostgreSQL	5432
📡 Endpoints principales (resumen)
Auth
Método	Endpoint	Descripción
POST	/auth/register	Registrar usuario
POST	/auth/login	Iniciar sesión
Branches
Método	Endpoint
GET	/branches
POST	/branches
PUT	/branches/{id}
Books
Método	Endpoint
GET	/books
POST	/books
GET	/books/{id}
PUT	/books/{id}
DELETE	/books/{id}
Loans
Método	Endpoint
POST	/loans
GET	/loans
GET	/loans/{id}
PATCH	/loans/{id}/status
⛓️ Ejemplos cURL
Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@library.com","password":"admin"}'

Crear libro
curl -X POST http://localhost:8000/api/v1/books \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
        "title":"Nuevo Libro",
        "author":"Autor",
        "isbn":"X-100",
        "branch_id":1,
        "total_copies":5
      }'

📊 Diagramas
ERD (ASCII)
 Users( id PK, name, email, role )
     │
     └──< Loans >──┐
                    │
              Books( id PK, isbn UNIQUE, branch_id FK )
                    │
                    └── LibraryBranches( id PK )

Flujo de préstamo
Member → REQUEST → Librarian APRROVE → BORROW → RETURN
                                     ↘ LOST
           BORROWED → OVERDUE (job)

🛣️ Roadmap

Implementar WebSockets para notificaciones

Admin dashboard (React)

Reportes PDF/Excel

Sistema de reservas de libros

Integración con proveedores externos ISBN


🙌 Contribuciones

Pull requests son bienvenidos.
Usa issues para sugerencias o reportar errores.