#configuracion de los test
import os
import sys
from pathlib import Path
from typing import Generator

import pytest
from fastapi.testclient import TestClient

# ======================================================
# Ajuste del sys.path para que 'app/' sea importable
# ======================================================
ROOT_DIR = Path(__file__).resolve().parents[1]  # .../library-management-api
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# ======================================================
# Imports de la aplicación
# ======================================================
from app.main import app
from app.db.session import SessionLocal
from app.db.models import User, UserRole, Loan
from app.core.security import hash_password


# ======================================================
# DB SESSION FIXTURE  (Agrega lo del startup del main)
# ======================================================
@pytest.fixture
def db_session() -> Generator:
    """
    Provee una sesión limpia de DB para cada test.
    """
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


# ======================================================
# CLIENT FIXTURE
# ======================================================
@pytest.fixture(scope="session")
def client():
    """
    TestClient de FastAPI (con contexto).
    """
    from starlette.testclient import TestClient

    with TestClient(app) as c:
        yield c


# ======================================================
# ADMIN FIXTURES
# ======================================================
@pytest.fixture(scope="session")
def admin_credentials():
    return {"email": "admin@library.local", "password": "admin123"}


@pytest.fixture(scope="session")
def admin_token(client: TestClient, admin_credentials):
    """
    Asegura que exista el admin embebido en la BD antes de login.
    """
    # 1) asegurar usuario admin en base de datos
    with SessionLocal() as db:
        user = db.query(User).filter(User.email == admin_credentials["email"]).first()
        if not user:
            user = User(
                email=admin_credentials["email"],
                full_name="Builtin Admin",
                hashed_password=hash_password(admin_credentials["password"]),
                role=UserRole.ADMIN,  # Ajusta si tu Enum es distinto
                is_active=True,
                is_blocked=False,
            )
            db.add(user)
            db.commit()

    # 2) login
    resp = client.post(
        "/api/v1/auth/login",
        data={
            "username": admin_credentials["email"],
            "password": admin_credentials["password"],
        },
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest.fixture
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


# ======================================================
# LIBRARIAN FIXTURES (NUEVO)
# ======================================================
@pytest.fixture(scope="session")
def librarian_credentials():
    return {"email": "librarian_test@example.com", "password": "librarian123"}


@pytest.fixture(scope="session")
def librarian_token(client: TestClient, librarian_credentials):
    """
    Crea (si no existe) un usuario LIBRARIAN y obtiene token JWT.
    """
    with SessionLocal() as db:
        user = db.query(User).filter(User.email == librarian_credentials["email"]).first()
        if not user:
            user = User(
                email=librarian_credentials["email"],
                full_name="Librarian Test",
                hashed_password=hash_password(librarian_credentials["password"]),
                role=UserRole.LIBRARIAN,
                is_active=True,
                is_blocked=False,
            )
            db.add(user)
            db.commit()

    resp = client.post(
        "/api/v1/auth/login",
        data={
            "username": librarian_credentials["email"],
            "password": librarian_credentials["password"],
        },
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest.fixture
def librarian_headers(librarian_token):
    return {"Authorization": f"Bearer {librarian_token}"}


# ======================================================
# MEMBER FIXTURES
# ======================================================
@pytest.fixture
def member_credentials(db_session):
    """Crea (si no existe) un usuario MEMBER de pruebas."""
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
    resp = client.post(
        "/api/v1/auth/login",
        data={
            "username": member_credentials["email"],
            "password": member_credentials["password"],
        },
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]

#Se limpian los loans para los tests
@pytest.fixture
def member_headers(member_token):
    return {"Authorization": f"Bearer {member_token}"}

def clear_member_loans():
    """
    Limpia todos los préstamos del member de prueba
    para que cada test empiece sin alcanzar el límite
    de préstamos activos.
    """
    with SessionLocal() as db:
        member = db.query(User).filter(User.email == "member_test@example.com").first()
        if member:
            db.query(Loan).filter(Loan.member_id == member.id).delete()
            db.commit()


@pytest.fixture
def clean_member_loans():
    """
    Fixture que limpia los préstamos del member antes de un test.
    Úsala en tests que crean loans para evitar chocar con el límite.
    """
    clear_member_loans()
    yield
    # opcional: podrías limpiar otra vez al final si quieres