from fastapi.testclient import TestClient
from datetime import datetime, timedelta, timezone

from app.db.session import SessionLocal
from app.db.models import Loan, User


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


def ensure_test_book(client: TestClient, admin_headers, branch_id: int) -> int:
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
        "isbn": f"TEST-ISBN-LOANS-{len(books) + 1}",
        "description": "Libro para pruebas de loans",
        "genre": "Test",
        "publication_year": 2025,
        "total_copies": 3,
        "branch_id": branch_id,
    }
    resp = client.post("/api/v1/books", json=payload, headers=admin_headers)
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def clear_member_loans():
    """
    Limpia todos los préstamos del miembro de prueba para que
    cada test empiece sin alcanzar el límite de 5 préstamos activos.
    """
    with SessionLocal() as db:
        member = db.query(User).filter(User.email == "member_test@example.com").first()
        if member:
            db.query(Loan).filter(Loan.member_id == member.id).delete()
            db.commit()


def test_loan_flow_member_request_and_admin_approves(
    client: TestClient,
    admin_headers,
    member_headers,
):
    # Asegurar que el miembro no tenga préstamos previos
    clear_member_loans()

    # 1) asegurar sucursal y libro
    branch_id = ensure_test_branch(client, admin_headers)
    book_id = ensure_test_book(client, admin_headers, branch_id)

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


def test_run_overdue_job_marks_borrowed_loan_as_overdue(
    client: TestClient,
    admin_headers,
    member_headers,
):
    # Asegurar que el miembro no tenga préstamos previos
    clear_member_loans()

    # 1) Asegurar sucursal y libro
    branch_id = ensure_test_branch(client, admin_headers)
    book_id = ensure_test_book(client, admin_headers, branch_id)

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