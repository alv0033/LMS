from fastapi import FastAPI, Depends
from fastapi.openapi.utils import get_openapi
from sqlalchemy.orm import Session

from app.api.v1.dependencies import get_db
from app.api.v1.endpoints import auth, branches
from app.db.session import SessionLocal
from app.services.init_admin import ensure_builtin_admin


app = FastAPI(
    title="Library Management API",
    version="1.0.0",
)

# Routers de la API v1
app.include_router(auth.router)
app.include_router(branches.router)


@app.on_event("startup")
def startup_event():
    db = SessionLocal()
    try:
        ensure_builtin_admin(db)
    finally:
        db.close()


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
