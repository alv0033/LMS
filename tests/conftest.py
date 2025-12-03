import os
import sys
from pathlib import Path

# Añadir la raíz del proyecto (directorio que contiene 'app/') al sys.path
ROOT_DIR = Path(__file__).resolve().parents[1]  # .../library-management-api
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import SessionLocal
from app.db.models import User, UserRole
from app.core.security import hash_password


@pytest.fixture(scope="session")
def db_session():
    """Sesión real a la BD (library_db)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session")
def client():
    """Cliente HTTP para llamar a la API."""
    return TestClient(app)


@pytest.fixture(scope="session")
def admin_credentials():
    """Credenciales del admin embebido."""
    return {"email": "admin@library.local", "password": "admin123"}


@pytest.fixture(scope="session")
def admin_token(client: TestClient, admin_credentials):
    """Obtiene un token JWT del admin embebido."""
    resp = client.post(
        "/api/v1/auth/login",
        data={
            "username": admin_credentials["email"],
            "password": admin_credentials["password"],
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    return data["access_token"]


@pytest.fixture
def admin_headers(admin_token):
    """Headers Authorization para peticiones autenticadas como admin."""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def member_credentials(db_session):
    """Crea (si no existe) un usuario MEMBER de pruebas y devuelve sus credenciales."""
    email = "member_test@example.com"
    password = "member123"

    user = db_session.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            email=email,
            full_name="Member Test",
            hashed_password=hash_password(password),
            role=UserRole.MEMBER,
            is_active=True,
            is_blocked=False,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

    return {"email": email, "password": password}


@pytest.fixture
def member_token(client: TestClient, member_credentials):
    """Token JWT para el member de prueba."""
    resp = client.post(
        "/api/v1/auth/login",
        data={
            "username": member_credentials["email"],
            "password": member_credentials["password"],
        },
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest.fixture
def member_headers(member_token):
    """Headers Authorization para member."""
    return {"Authorization": f"Bearer {member_token}"}
