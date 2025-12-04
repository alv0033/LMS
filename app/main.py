from fastapi import FastAPI, Depends, Request
from fastapi.responses import Response
from fastapi.openapi.utils import get_openapi
import time
import uuid
import logging

from sqlalchemy.orm import Session

from app.api.v1.dependencies import get_db
from app.api.v1.endpoints import auth, branches, books, loans, users
from app.api.v1.endpoints import admin as admin_endpoints
from app.db.session import SessionLocal
from app.services.init_admin import ensure_builtin_admin
from app.core.config import settings
from app.core.logging import configure_logging, get_logger, request_id_ctx


# Configurar logging global al arrancar el módulo
configure_logging()
request_logger = get_logger("api.request")

app = FastAPI(
    title="Library Management API",
    version="1.0.0",
)

# Routers de la API 
app.include_router(auth.router)
app.include_router(branches.router)
app.include_router(books.router)
app.include_router(loans.router)
app.include_router(users.router) 
app.include_router(admin_endpoints.router)


@app.on_event("startup")
def startup_event():
    db = SessionLocal()
    configure_logging()
    try:
        ensure_builtin_admin(db)
    finally:
        db.close()


@app.middleware("http")
async def add_request_id_and_log(request: Request, call_next):
    """
    Middleware que:
    - Asigna un request_id (si no viene en cabecera).
    - Mide el tiempo de respuesta.
    - Loguea la petición y marca WARNING si es lenta.
    """
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    start = time.perf_counter()

    # Guardamos el request_id en el estado del request para que otros lo usen si quieren
    request.state.request_id = request_id
    request_id_ctx.set(request_id)


    try:
        response: Response = await call_next(request)
    except Exception as exc:
        # Log de error con stacktrace
        process_time_ms = (time.perf_counter() - start) * 1000
        request_logger.error(
            "unhandled_exception",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": 500,
                "duration_ms": round(process_time_ms, 2),
                "client_host": request.client.host if request.client else None,
            },
            exc_info=True,
        )
        raise

    process_time_ms = (time.perf_counter() - start) * 1000
    response.headers["X-Request-ID"] = request_id

    # Elegir nivel según si es lenta
    level = "INFO"
    if process_time_ms > settings.SLOW_REQUEST_THRESHOLD_MS:
        level = "WARNING"

    request_logger.log(
        level=logging.INFO,
        msg="request_completed",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": round(process_time_ms, 2),
            "client_host": request.client.host if request.client else None,
        },
    )

    return response


@app.get("/")
def root():
    return {"message": "Library API running"}


@app.get("/health/db")
def health_db(db: Session = Depends(get_db)):
    db.execute("SELECT 1")
    return {"status": "ok"}


def custom_openapi():
    """
    Solo definimos el esquema OAuth2 password para que Swagger
    muestre el cuadro de 'Authorize' con username/password.

    NO aplicamos seguridad global: cada endpoint que use
    get_current_user tendrá su propia sección de seguridad.
    """
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="Library Management API",
        version="1.0.0",
        routes=app.routes,
    )

    components = openapi_schema.setdefault("components", {})
    security_schemes = components.setdefault("securitySchemes", {})

    # Debe llamarse igual que el esquema definido con OAuth2PasswordBearer
    security_schemes["OAuth2PasswordBearer"] = {
        "type": "oauth2",
        "flows": {
            "password": {
                "tokenUrl": "/api/v1/auth/login",
                "scopes": {},
            }
        },
    }

    # IMPORTANTE: aquí ya NO ponemos openapi_schema["security"] global
    # De esta forma, solo los endpoints que dependen de get_current_user
    # quedarán marcados como protegidos en el esquema OpenAPI.

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi
