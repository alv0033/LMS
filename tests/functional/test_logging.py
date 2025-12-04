import uuid
from typing import Dict
import logging

from fastapi.testclient import TestClient

#crea un ISBN unico y corto para los tests
def _unique_isbn(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"

#crea una sucursal para los tests
def _create_branch(client: TestClient, admin_headers: Dict, name: str, email: str) -> Dict:
    resp = client.post(
        "/api/v1/branches",
        json={
            "name": name,
            "address": "Calle Logging 123",
            "description": "Sucursal logging",
            "phone_number": "555-111-2222",
            "email": email,
            "is_active": True,
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()

#crea un libro para los tests
def _create_book(
    client: TestClient,
    admin_headers: Dict,
    branch_id: int,
    title: str,
    isbn_prefix: str,
) -> Dict:
    isbn = _unique_isbn(isbn_prefix)
    resp = client.post(
        "/api/v1/books",
        json={
            "title": title,
            "author": "Autor Logging",
            "isbn": isbn,
            "description": "Libro logging",
            "genre": "Test",
            "publication_year": 2020,
            "total_copies": 3,
            "branch_id": branch_id,
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()

# obtiene el id del admin user
def _get_admin_user_id(client: TestClient, admin_headers: Dict) -> int:
    """
    Obtiene el id del admin buscando por email.
    Ajusta el email si tu admin usa otro.
    """
    resp = client.get("/api/v1/users", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    users = resp.json()
    admin = next(
        (u for u in users if u.get("email") == "admin@library.local"),
        None,
    )
    assert admin is not None, "No se encontró el usuario admin@library.local en /users"
    return admin["id"]

# funciones auxiliares para logs
def _logs_messages(caplog) -> list[str]:
    return [record.getMessage() for record in caplog.records]

#devuelve todo el texto de los logs capturados
def _logs_text(caplog) -> str:
    return "\n".join(_logs_messages(caplog))

#verifica logs de login
def test_logging_login_success(client: TestClient, caplog):
    """
    Debe loguear un intento de login exitoso con mensaje login_success.
    """
    caplog.set_level(logging.INFO)

    resp = client.post(
        "/api/v1/auth/login",
        data={"username": "admin@library.local", "password": "admin123"},
    )
    assert resp.status_code == 200, resp.text

    log_text = _logs_text(caplog)

    # Según lo que viste en el fallo: aparece 'login_success'
    assert "login_success" in log_text

#verifica logs de login fallido
def test_logging_login_failure(client: TestClient, caplog):
    """
    Debe loguear un intento de login fallido con mensaje login_failed.
    """
    caplog.set_level(logging.INFO)

    resp = client.post(
        "/api/v1/auth/login",
        data={"username": "admin@library.local", "password": "wrong"},
    )
    assert resp.status_code == 401, resp.text

    log_text = _logs_text(caplog)

    # Según lo que viste en el fallo: aparece 'login_failed'
    assert "login_failed" in log_text


#verifica logs de creación de sucursal
def test_logging_branch_create(
    client: TestClient,
    admin_headers,
    caplog,
):
    """
    Verifica que al crear una sucursal se genere al menos un log de request_completed.
    """
    caplog.set_level(logging.INFO)

    _ = _create_branch(
        client,
        admin_headers,
        "Branch Logging",
        "branch_logging@library.com",
    )

    messages = _logs_messages(caplog)

    # Verificamos que haya al menos un log de "request_completed"
    assert any("request_completed" in m for m in messages)

#verifica que librarian no puede borrar sucursal y el log
def test_logging_branch_delete_forbidden_for_librarian(
    client: TestClient,
    admin_headers,
    librarian_headers,
    caplog,
):
    """
    Librarian no puede borrar una sucursal.
    Debe devolver 403 y generar logs (request_completed).
    """
    caplog.set_level(logging.INFO)

    branch = _create_branch(
        client,
        admin_headers,
        "Branch Delete Forbidden",
        "branch_delete_forbidden@library.com",
    )
    branch_id = branch["id"]

    resp = client.delete(f"/api/v1/branches/{branch_id}", headers=librarian_headers)
    assert resp.status_code == 403, resp.text

    messages = _logs_messages(caplog)

    assert any("request_completed" in m for m in messages)


#verifica logs de creación de libro
def test_logging_book_create(client: TestClient, admin_headers, caplog):
    """
    Verifica que al crear un libro se generen logs (request_completed).
    """
    caplog.set_level(logging.INFO)

    branch = _create_branch(
        client,
        admin_headers,
        "Branch BookLogging",
        "branch_booklogging@library.com",
    )
    branch_id = branch["id"]

    payload = {
        "title": "Libro Logging",
        "author": "Autor Logging",
        "isbn": _unique_isbn("LOG-BOOK"),
        "description": "Libro para logging",
        "genre": "Test",
        "publication_year": 2024,
        "total_copies": 3,
        "branch_id": branch_id,
    }

    resp = client.post("/api/v1/books", json=payload, headers=admin_headers)
    assert resp.status_code == 201, resp.text

    messages = _logs_messages(caplog)

    assert any("request_completed" in m for m in messages)

#verifica logs de actualización de libro
def test_logging_book_update(client: TestClient, admin_headers, caplog):
    """
    Verifica que al actualizar un libro se generen logs (request_completed).
    """
    caplog.set_level(logging.INFO)

    branch = _create_branch(
        client,
        admin_headers,
        "Branch BookUpdate",
        "branch_bookupdate@library.com",
    )
    branch_id = branch["id"]

    book = _create_book(
        client,
        admin_headers,
        branch_id,
        title="Libro Update",
        isbn_prefix="LOG-UPDATE",
    )
    book_id = book["id"]

    resp_upd = client.put(
        f"/api/v1/books/{book_id}",
        json={"title": "Libro Update 2"},
        headers=admin_headers,
    )
    assert resp_upd.status_code == 200, resp_upd.text

    messages = _logs_messages(caplog)

    assert any("request_completed" in m for m in messages)


#verifica logs de cambio de estado de préstamo
def test_logging_loan_status_change(
    client: TestClient,
    admin_headers,
    member_headers,
    caplog,
):
    """
    Verifica que al cambiar el estado de un préstamo
    se generen logs (request_completed).
    """
    caplog.set_level(logging.INFO)

    branch = _create_branch(
        client,
        admin_headers,
        "Branch LoanLog",
        "branch_loanlog@library.com",
    )
    branch_id = branch["id"]

    book = _create_book(
        client,
        admin_headers,
        branch_id,
        title="Libro LoanLog",
        isbn_prefix="LOG-LOAN",
    )
    book_id = book["id"]

    # Member crea préstamo (REQUESTED)
    resp_loan = client.post(
        "/api/v1/loans",
        json={"book_id": book_id, "branch_id": branch_id},
        headers=member_headers,
    )
    assert resp_loan.status_code == 201, resp_loan.text
    loan = resp_loan.json()

    # Admin aprueba -> APPROVED
    resp_approve = client.patch(
        f"/api/v1/loans/{loan['id']}/status",
        json={"new_status": "APPROVED"},
        headers=admin_headers,
    )
    assert resp_approve.status_code == 200, resp_approve.text

    messages = _logs_messages(caplog)

    assert any("request_completed" in m for m in messages)


#verifica que no se pueda borrar el admin built-in y el log
def test_logging_builtin_admin_delete_fails(
    client: TestClient,
    admin_headers,
    caplog,
):
    """
    Verifica que al intentar borrar el built-in admin
    se genera un error (400/403) y logs (request_completed).
    """
    caplog.set_level(logging.INFO)

    admin_id = _get_admin_user_id(client, admin_headers)

    resp = client.delete(f"/api/v1/users/{admin_id}", headers=admin_headers)
    # según tu implementación puede ser 400 o 403
    assert resp.status_code in (400, 403), resp.text

    messages = _logs_messages(caplog)

    assert any("request_completed" in m for m in messages)
