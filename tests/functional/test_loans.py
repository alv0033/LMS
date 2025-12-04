import uuid
import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta, timezone

from app.db.session import SessionLocal
from app.db.models import Loan

# Aplica clean_member_loans a todos los tests de este archivo
pytestmark = pytest.mark.usefixtures("clean_member_loans")

#Garantizar una sucursal de prueba y la devuelve si existe, la crea si no
def ensure_test_branch(client: TestClient, admin_headers) -> int:
    resp = client.get("/api/v1/branches", headers=admin_headers)
    assert resp.status_code == 200
    branches = resp.json()
    if branches:
        return branches[0]["id"]

    # Crear una si no existe
    payload = {
        "name": "Sucursal Loans",
        "address": "Av Loans 1",
        "description": "Sucursal para pruebas de préstamos",
        "phone_number": "555-111-1111",
        "email": "loans_branch@library.local",
        "is_active": True,
    }
    resp = client.post("/api/v1/branches", json=payload, headers=admin_headers)
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]

#Garantizar un libro de prueba y la devuelve si existe, la crea si no
def ensure_test_book(
    client: TestClient,
    admin_headers,
    branch_id: int,
    unique_isbn,
) -> int:
    resp = client.get("/api/v1/books", headers=admin_headers)
    assert resp.status_code == 200
    books = resp.json()

    # 1) Intentar reutilizar un libro de esta sucursal que tenga copias disponibles
    for b in books:
        if b["branch_id"] == branch_id and b.get("available_copies", 0) > 0:
            return b["id"]

    # 2) Si no hay ninguno con copias disponibles, crear uno nuevo
    payload = {
        "title": "Libro de Pruebas",
        "author": "Autor Test",
        "isbn": unique_isbn("LOANS"),
        "description": "Libro para pruebas de loans",
        "genre": "Test",
        "publication_year": 2025,
        "total_copies": 3,
        "branch_id": branch_id,
    }
    resp = client.post("/api/v1/books", json=payload, headers=admin_headers)
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]

#test funcional del flujo de loan completo
def test_loan_flow_member_request_and_admin_approves(
    client: TestClient,
    admin_headers,
    member_headers,
    unique_isbn,
):
    # 1) asegurar sucursal y libro
    branch_id = ensure_test_branch(client, admin_headers)
    book_id = ensure_test_book(client, admin_headers, branch_id, unique_isbn)

    # 2) member crea un préstamo (REQUESTED)
    loan_payload = {
        "book_id": book_id,
        "branch_id": branch_id,
    }
    resp = client.post("/api/v1/loans", json=loan_payload, headers=member_headers)
    assert resp.status_code == 201, resp.text
    loan = resp.json()
    assert loan["status"] == "REQUESTED"
    loan_id = loan["id"]

    # 3) admin cambia estado a APPROVED
    resp = client.patch(
        f"/api/v1/loans/{loan_id}/status",
        json={"new_status": "APPROVED"},
        headers=admin_headers,
    )
    assert resp.status_code == 200, resp.text
    loan = resp.json()
    assert loan["status"] == "APPROVED"

    # 4) admin cambia estado a BORROWED
    resp = client.patch(
        f"/api/v1/loans/{loan_id}/status",
        json={"new_status": "BORROWED"},
        headers=admin_headers,
    )
    assert resp.status_code == 200, resp.text
    loan = resp.json()
    assert loan["status"] == "BORROWED"

#Test funcional del job de overdue (aplicar la fee)
def test_run_overdue_job_marks_borrowed_loan_as_overdue(
    client: TestClient,
    admin_headers,
    member_headers,
    unique_isbn,
):
    # 1) Asegurar sucursal y libro
    branch_id = ensure_test_branch(client, admin_headers)
    book_id = ensure_test_book(client, admin_headers, branch_id, unique_isbn)

    # 2) Member crea un préstamo (REQUESTED)
    loan_payload = {
        "book_id": book_id,
        "branch_id": branch_id,
    }
    resp = client.post("/api/v1/loans", json=loan_payload, headers=member_headers)
    assert resp.status_code == 201, resp.text
    loan = resp.json()
    loan_id = loan["id"]
    assert loan["status"] == "REQUESTED"

    # 3) Admin cambia el estado a APPROVED (respeta el flujo REQUESTED -> APPROVED)
    resp = client.patch(
        f"/api/v1/loans/{loan_id}/status",
        json={"new_status": "APPROVED"},
        headers=admin_headers,
    )
    assert resp.status_code == 200, resp.text
    loan = resp.json()
    assert loan["status"] == "APPROVED"

    # 4) Admin cambia el estado a BORROWED (APPROVED -> BORROWED)
    resp = client.patch(
        f"/api/v1/loans/{loan_id}/status",
        json={"new_status": "BORROWED"},
        headers=admin_headers,
    )
    assert resp.status_code == 200, resp.text
    loan = resp.json()
    assert loan["status"] == "BORROWED"

    # 5) Forzar due_date al pasado (3 días atrás) directamente en la base de datos
    with SessionLocal() as db:
        db_loan = db.query(Loan).filter(Loan.id == loan_id).first()
        assert db_loan is not None
        db_loan.due_date = datetime.now(timezone.utc) - timedelta(days=3)
        db.commit()

    # 6) Ejecutar el job de overdue
    resp = client.post("/api/v1/loans/run-overdue-job", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["updated_overdue_loans"] >= 1

    # 7) Verificar que el préstamo ahora está OVERDUE y con multa > 0
    resp = client.get(f"/api/v1/loans/{loan_id}", headers=member_headers)
    assert resp.status_code == 200, resp.text
    loan = resp.json()
    assert loan["status"] == "OVERDUE"
    assert loan["late_fee_amount"] > 0


#test funcional de cancelación de préstamo por el member
def test_member_can_cancel_requested_loan(
    client: TestClient,
    admin_headers,
    member_headers,
    unique_isbn,
):
    """
    Member puede cancelar un préstamo en estado REQUESTED.
    """

    # Crear sucursal propia para el test
    resp_branch = client.post(
        "/api/v1/branches",
        json={
            "name": "Branch CancelOK",
            "address": "Calle 1",
            "description": "Test cancel",
            "phone_number": "555-000",
            "email": "cancelok@library.local",
            "is_active": True,
        },
        headers=admin_headers,
    )
    assert resp_branch.status_code == 201, resp_branch.text
    branch_id = resp_branch.json()["id"]

    # Crear libro
    resp_book = client.post(
        "/api/v1/books",
        json={
            "title": "Libro CancelOK",
            "author": "Autor",
            "isbn": unique_isbn("CAN-OK"),
            "description": "desc",
            "genre": "Test",
            "publication_year": 2024,
            "total_copies": 3,
            "branch_id": branch_id,
        },
        headers=admin_headers,
    )
    assert resp_book.status_code == 201, resp_book.text
    book_id = resp_book.json()["id"]

    # Member crea préstamo (REQUESTED)
    resp_loan = client.post(
        "/api/v1/loans",
        json={"book_id": book_id, "branch_id": branch_id},
        headers=member_headers,
    )
    assert resp_loan.status_code == 201, resp_loan.text
    loan = resp_loan.json()
    assert loan["status"] == "REQUESTED"

    # Member cancela antes de aprobación
    resp_cancel = client.patch(
        f"/api/v1/loans/{loan['id']}/status",
        json={"new_status": "CANCELED"},
        headers=member_headers,
    )
    assert resp_cancel.status_code == 200, resp_cancel.text
    loan_cancelled = resp_cancel.json()
    assert loan_cancelled["status"] == "CANCELED"

#test funcional para validar el máximo de préstamos activos por miembro
def test_member_cannot_exceed_max_active_loans(
    client: TestClient,
    admin_headers,
    member_headers,
    unique_isbn,
):
    """
    Valida la regla de negocio: máximo número de préstamos activos por miembro.
    Se asume un límite de 5 (según tu mensaje de error actual).
    """

    # Crear sucursal
    resp_branch = client.post(
        "/api/v1/branches",
        json={
            "name": "Branch MaxLoans",
            "address": "Dir",
            "description": "MaxLoans",
            "phone_number": "555-111",
            "email": "maxloans@library.local",
            "is_active": True,
        },
        headers=admin_headers,
    )
    assert resp_branch.status_code == 201, resp_branch.text
    branch_id = resp_branch.json()["id"]

    # Crear libro con muchas copias para no topar con la regla de copias
    resp_book = client.post(
        "/api/v1/books",
        json={
            "title": "Libro MaxLoans",
            "author": "Autor",
            "isbn": unique_isbn("MAX-LOAN"),
            "description": "desc",
            "genre": "Test",
            "publication_year": 2024,
            "total_copies": 50,
            "branch_id": branch_id,
        },
        headers=admin_headers,
    )
    assert resp_book.status_code == 201, resp_book.text
    book_id = resp_book.json()["id"]

    # Crear 5 préstamos válidos
    for _ in range(5):
        resp = client.post(
            "/api/v1/loans",
            json={"book_id": book_id, "branch_id": branch_id},
            headers=member_headers,
        )
        assert resp.status_code == 201, resp.text

    # Intentar sexto préstamo -> debe fallar por límite de préstamos activos
    resp_sixth = client.post(
        "/api/v1/loans",
        json={"book_id": book_id, "branch_id": branch_id},
        headers=member_headers,
    )
    assert resp_sixth.status_code in (400, 409), resp_sixth.text
    assert "maximum number of active loans" in resp_sixth.text.lower()

#Test funcional del retorno de un préstamo sin multa
def test_loan_returned_without_late_fee(
    client: TestClient,
    admin_headers,
    member_headers,
    unique_isbn,
):
    """
    Flujo REQUESTED -> APPROVED -> BORROWED -> RETURNED sin overdue:
    late_fee_amount debe ser 0.
    """

    # Crear sucursal y libro
    resp_branch = client.post(
        "/api/v1/branches",
        json={
            "name": "Branch ReturnOK",
            "address": "Dir",
            "description": "Return",
            "phone_number": "555-123",
            "email": "returnok@library.local",
            "is_active": True,
        },
        headers=admin_headers,
    )
    assert resp_branch.status_code == 201, resp_branch.text
    branch_id = resp_branch.json()["id"]

    resp_book = client.post(
        "/api/v1/books",
        json={
            "title": "Libro Return",
            "author": "Autor",
            "isbn": unique_isbn("RETURN"),
            "description": "desc",
            "genre": "Test",
            "publication_year": 2024,
            "total_copies": 2,
            "branch_id": branch_id,
        },
        headers=admin_headers,
    )
    assert resp_book.status_code == 201, resp_book.text
    book_id = resp_book.json()["id"]

    # Member crea préstamo
    resp_loan = client.post(
        "/api/v1/loans",
        json={"book_id": book_id, "branch_id": branch_id},
        headers=member_headers,
    )
    assert resp_loan.status_code == 201, resp_loan.text
    loan = resp_loan.json()
    loan_id = loan["id"]
    assert loan["status"] == "REQUESTED"

    # Admin: REQUESTED -> APPROVED -> BORROWED
    for status in ["APPROVED", "BORROWED"]:
        resp = client.patch(
            f"/api/v1/loans/{loan_id}/status",
            json={"new_status": status},
            headers=admin_headers,
        )
        assert resp.status_code == 200, resp.text
        loan = resp.json()
        assert loan["status"] == status

    # Admin lo marca como RETURNED (no overdue)
    resp_return = client.patch(
        f"/api/v1/loans/{loan_id}/status",
        json={"new_status": "RETURNED"},
        headers=admin_headers,
    )
    assert resp_return.status_code == 200, resp_return.text
    loan_returned = resp_return.json()
    assert loan_returned["status"] == "RETURNED"
    assert loan_returned.get("late_fee_amount", 0) == 0

#test funcional del retorno de un préstamo con multa
def test_overdue_loan_returned_keeps_late_fee(
    client: TestClient,
    admin_headers,
    member_headers,
    unique_isbn,
):
    """
    Préstamo BORROWED con due_date en el pasado:
    - Job de overdue lo marca OVERDUE y asigna late_fee.
    - Luego se marca RETURNED y la multa debe seguir siendo > 0.
    """

    # Crear sucursal y libro
    resp_branch = client.post(
        "/api/v1/branches",
        json={
            "name": "Branch ReturnOverdue",
            "address": "Dir",
            "description": "ReturnOverdue",
            "phone_number": "555-124",
            "email": "returnoverdue@library.local",
            "is_active": True,
        },
        headers=admin_headers,
    )
    assert resp_branch.status_code == 201, resp_branch.text
    branch_id = resp_branch.json()["id"]

    resp_book = client.post(
        "/api/v1/books",
        json={
            "title": "Libro Return Overdue",
            "author": "Autor",
            "isbn": unique_isbn("RETOVER"),  # << antes era "RETURN-OVERDUE-123"
            "description": "desc",
            "genre": "Test",
            "publication_year": 2024,
            "total_copies": 2,
            "branch_id": branch_id,
        },
        headers=admin_headers,
    )
    assert resp_book.status_code == 201, resp_book.text
    book_id = resp_book.json()["id"]

    # Member crea préstamo
    resp_loan = client.post(
        "/api/v1/loans",
        json={"book_id": book_id, "branch_id": branch_id},
        headers=member_headers,
    )
    assert resp_loan.status_code == 201, resp_loan.text
    loan = resp_loan.json()
    loan_id = loan["id"]

    # Admin: REQUESTED -> APPROVED -> BORROWED
    for status in ["APPROVED", "BORROWED"]:
        resp = client.patch(
            f"/api/v1/loans/{loan_id}/status",
            json={"new_status": status},
            headers=admin_headers,
        )
        assert resp.status_code == 200, resp.text

    # Forzar due_date al pasado
    with SessionLocal() as db:
        db_loan = db.query(Loan).filter(Loan.id == loan_id).first()
        assert db_loan is not None
        db_loan.due_date = datetime.now(timezone.utc) - timedelta(days=5)
        db.commit()

    # Ejecutar job de overdue
    resp_job = client.post("/api/v1/loans/run-overdue-job", headers=admin_headers)
    assert resp_job.status_code == 200, resp_job.text

    # Verificar OVERDUE con multa > 0
    resp = client.get(f"/api/v1/loans/{loan_id}", headers=member_headers)
    assert resp.status_code == 200, resp.text
    loan = resp.json()
    assert loan["status"] == "OVERDUE"
    assert loan["late_fee_amount"] > 0

    # Ahora marcar RETURNED y la multa debe seguir > 0
    resp_return = client.patch(
        f"/api/v1/loans/{loan_id}/status",
        json={"new_status": "RETURNED"},
        headers=admin_headers,
    )
    assert resp_return.status_code == 200, resp_return.text
    loan_returned = resp_return.json()
    assert loan_returned["status"] == "RETURNED"
    assert loan_returned["late_fee_amount"] > 0

#test funcional del flujo de loan lost
def test_loan_lost_flow(
    client: TestClient,
    admin_headers,
    member_headers,
    unique_isbn,
):
    """
    Flujo REQUESTED -> APPROVED -> BORROWED -> LOST.
    """

    # Crear sucursal y libro
    resp_branch = client.post(
        "/api/v1/branches",
        json={
            "name": "Branch Lost",
            "address": "Dir",
            "description": "Lost",
            "phone_number": "555-321",
            "email": "lost@library.local",
            "is_active": True,
        },
        headers=admin_headers,
    )
    assert resp_branch.status_code == 201, resp_branch.text
    branch_id = resp_branch.json()["id"]

    resp_book = client.post(
        "/api/v1/books",
        json={
            "title": "Libro Lost",
            "author": "Autor",
            "isbn": unique_isbn("LOST"),
            "description": "desc",
            "genre": "Test",
            "publication_year": 2024,
            "total_copies": 2,
            "branch_id": branch_id,
        },
        headers=admin_headers,
    )
    assert resp_book.status_code == 201, resp_book.text
    book_id = resp_book.json()["id"]

    # Member solicita
    resp_loan = client.post(
        "/api/v1/loans",
        json={"book_id": book_id, "branch_id": branch_id},
        headers=member_headers,
    )
    assert resp_loan.status_code == 201, resp_loan.text
    loan = resp_loan.json()
    loan_id = loan["id"]

    # Admin: APPROVED -> BORROWED -> LOST
    for status in ["APPROVED", "BORROWED", "LOST"]:
        resp = client.patch(
            f"/api/v1/loans/{loan_id}/status",
            json={"new_status": status},
            headers=admin_headers,
        )
        assert resp.status_code == 200, resp.text

    resp_final = client.get(f"/api/v1/loans/{loan_id}", headers=member_headers)
    assert resp_final.status_code == 200, resp_final.text
    loan_final = resp_final.json()
    assert loan_final["status"] == "LOST"

#test funcional del historial de cambios de estado del préstamo
def test_loan_history_records_changes(
    client: TestClient,
    admin_headers,
    member_headers,
    unique_isbn,
):
    """
    Verifica que el préstamo cambie de estado en el orden correcto
    REQUESTED -> APPROVED -> BORROWED, consultando el detalle tras cada cambio.
    (No asume un campo 'history' en la respuesta.)
    """

    # Crear sucursal y libro
    resp_branch = client.post(
        "/api/v1/branches",
        json={
            "name": "Branch Hist",
            "address": "Dir",
            "description": "Hist",
            "phone_number": "555-222",
            "email": "hist@library.local",
            "is_active": True,
        },
        headers=admin_headers,
    )
    assert resp_branch.status_code == 201, resp_branch.text
    branch_id = resp_branch.json()["id"]

    resp_book = client.post(
        "/api/v1/books",
        json={
            "title": "Libro Hist",
            "author": "Autor",
            "isbn": unique_isbn("HIST"),
            "description": "desc",
            "genre": "Test",
            "publication_year": 2024,
            "total_copies": 2,
            "branch_id": branch_id,
        },
        headers=admin_headers,
    )
    assert resp_book.status_code == 201, resp_book.text
    book_id = resp_book.json()["id"]

    # REQUESTED
    resp_loan = client.post(
        "/api/v1/loans",
        json={"book_id": book_id, "branch_id": branch_id},
        headers=member_headers,
    )
    assert resp_loan.status_code == 201, resp_loan.text
    loan = resp_loan.json()
    loan_id = loan["id"]

    # Verificar estado inicial REQUESTED
    resp_detail = client.get(f"/api/v1/loans/{loan_id}", headers=admin_headers)
    assert resp_detail.status_code == 200, resp_detail.text
    data = resp_detail.json()
    assert data["status"] == "REQUESTED"

    # APPROVED
    resp_approved = client.patch(
        f"/api/v1/loans/{loan_id}/status",
        json={"new_status": "APPROVED"},
        headers=admin_headers,
    )
    assert resp_approved.status_code == 200, resp_approved.text

    resp_detail = client.get(f"/api/v1/loans/{loan_id}", headers=admin_headers)
    assert resp_detail.status_code == 200, resp_detail.text
    data = resp_detail.json()
    assert data["status"] == "APPROVED"

    # BORROWED
    resp_borrowed = client.patch(
        f"/api/v1/loans/{loan_id}/status",
        json={"new_status": "BORROWED"},
        headers=admin_headers,
    )
    assert resp_borrowed.status_code == 200, resp_borrowed.text

    resp_detail = client.get(f"/api/v1/loans/{loan_id}", headers=admin_headers)
    assert resp_detail.status_code == 200, resp_detail.text
    data = resp_detail.json()
    assert data["status"] == "BORROWED"

#test funcional del historial de préstamos del miembro autenticado
def test_my_history_returns_only_member_loans(
    client: TestClient,
    admin_headers,
    member_headers,
    unique_isbn,
):
    """
    Verifica que /api/v1/loans/my-history devuelva los préstamos
    del miembro autenticado. Aquí se limpia primero todo para que
    solo existan los préstamos creados en este test.
    """

    # Crear sucursal y libro
    resp_branch = client.post(
        "/api/v1/branches",
        json={
            "name": "Branch MyHist",
            "address": "Dir",
            "description": "MyHist",
            "phone_number": "555-333",
            "email": "myhist@library.local",
            "is_active": True,
        },
        headers=admin_headers,
    )
    assert resp_branch.status_code == 201, resp_branch.text
    branch_id = resp_branch.json()["id"]

    resp_book = client.post(
        "/api/v1/books",
        json={
            "title": "Libro MyHist",
            "author": "Autor",
            "isbn": unique_isbn("MYHIST"),
            "description": "desc",
            "genre": "Test",
            "publication_year": 2024,
            "total_copies": 5,
            "branch_id": branch_id,
        },
        headers=admin_headers,
    )
    assert resp_book.status_code == 201, resp_book.text
    book_id = resp_book.json()["id"]

    # Crear 2 préstamos para este miembro
    for _ in range(2):
        resp_loan = client.post(
            "/api/v1/loans",
            json={"book_id": book_id, "branch_id": branch_id},
            headers=member_headers,
        )
        assert resp_loan.status_code == 201, resp_loan.text

    # Consultar my-history
    resp_history = client.get("/api/v1/loans/my-history", headers=member_headers)
    assert resp_history.status_code == 200, resp_history.text
    loans = resp_history.json()

    # Como limpiamos antes, deben ser exactamente 2
    assert isinstance(loans, list)
    assert len(loans) == 2

#test funcional del filtrado de préstamos por estado 
def test_filter_loans_by_status_query_param(
    client: TestClient,
    admin_headers,
    member_headers,
    unique_isbn,
):
    """
    Verifica filtrado de préstamos por status usando query param:
    GET /api/v1/loans?status=APPROVED
    """

    # Crear sucursal y libro
    resp_branch = client.post(
        "/api/v1/branches",
        json={
            "name": "Branch FilterStatus",
            "address": "Dir",
            "description": "FS",
            "phone_number": "555-444",
            "email": "filterstatus@library.local",
            "is_active": True,
        },
        headers=admin_headers,
    )
    assert resp_branch.status_code == 201, resp_branch.text
    branch_id = resp_branch.json()["id"]

    resp_book = client.post(
        "/api/v1/books",
        json={
            "title": "Libro FS",
            "author": "Autor",
            "isbn": unique_isbn("FILTERSTAT"),  # << antes era "FILTER-LOAN-STATUS-1"
            "description": "desc",
            "genre": "Test",
            "publication_year": 2024,
            "total_copies": 5,
            "branch_id": branch_id,
        },
        headers=admin_headers,
    )
    assert resp_book.status_code == 201, resp_book.text
    book_id = resp_book.json()["id"]

    # Crear préstamo y pasar a APPROVED
    resp_loan = client.post(
        "/api/v1/loans",
        json={"book_id": book_id, "branch_id": branch_id},
        headers=member_headers,
    )
    assert resp_loan.status_code == 201, resp_loan.text
    loan = resp_loan.json()
    loan_id = loan["id"]

    resp_approve = client.patch(
        f"/api/v1/loans/{loan_id}/status",
        json={"new_status": "APPROVED"},
        headers=admin_headers,
    )
    assert resp_approve.status_code == 200, resp_approve.text

    # Llamar a /loans filtrando por status=APPROVED
    resp_list = client.get(
        "/api/v1/loans?status=APPROVED",
        headers=admin_headers,
    )
    assert resp_list.status_code == 200, resp_list.text
    loans = resp_list.json()
    assert isinstance(loans, list)

    # Todos los devueltos deben ser APPROVED, y nuestro préstamo debe estar ahí
    assert all(l["status"] == "APPROVED" for l in loans)
    assert any(l["id"] == loan_id for l in loans)