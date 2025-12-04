import uuid
from datetime import datetime, timedelta
from typing import Dict

from fastapi.testclient import TestClient


def _unique_isbn(prefix: str) -> str:
    return f"{prefix}{uuid.uuid4().hex[:7]}"  ##Generador de ISBN único


def _create_branch(client: TestClient, admin_headers: Dict, name: str, email: str) -> int:
    resp = client.post(
        "/api/v1/branches",
        json={
            "name": name,
            "address": "Calle Edge 123",
            "description": "Sucursal edge cases",
            "phone_number": "555-999-0000",
            "email": email,
            "is_active": True,
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _create_book_one_copy(
    client: TestClient,
    admin_headers: Dict,
    branch_id: int,
    title: str,
    isbn_prefix: str,
) -> int:
    isbn = _unique_isbn(isbn_prefix)
    resp = client.post(
        "/api/v1/books",
        json={
            "title": title,
            "author": "Autor Edge",
            "isbn": isbn,
            "description": "Libro edge case",
            "genre": "Test",
            "publication_year": 2021,
            "total_copies": 1,
            "branch_id": branch_id,
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def test_request_loan_no_available_copies(
    client: TestClient,
    admin_headers,
    member_headers,
):
    """
    Edge case: no hay copias disponibles.
    - total_copies = 1
    - Un préstamo BORROWED ocupa esa copia
    - Un segundo member intenta pedirlo -> debería fallar (400 o 409).
    """
    branch_id = _create_branch(
        client,
        admin_headers,
        "Branch NoCopies",
        "branch_nocopies@library.local",
    )

    book_id = _create_book_one_copy(
        client,
        admin_headers,
        branch_id,
        title="Libro sin copias",
        isbn_prefix="EDGE-NOCOPIES",
    )

    # Primer member pide préstamo -> REQUESTED
    resp_loan1 = client.post(
        "/api/v1/loans",
        json={"book_id": book_id, "branch_id": branch_id},
        headers=member_headers,
    )
    assert resp_loan1.status_code == 201, resp_loan1.text
    loan1 = resp_loan1.json()

    # ADMIN aprueba y marca BORROWED para que consuma la copia
    resp_approve = client.patch(
        f"/api/v1/loans/{loan1['id']}/status",
        json={"new_status": "APPROVED"},
        headers=admin_headers,
    )
    assert resp_approve.status_code == 200, resp_approve.text

    resp_borrow = client.patch(
        f"/api/v1/loans/{loan1['id']}/status",
        json={"new_status": "BORROWED"},
        headers=admin_headers,
    )
    assert resp_borrow.status_code == 200, resp_borrow.text

    # Segundo member (mismo token member_headers, para simplificar) intenta pedirlo
    resp_loan2 = client.post(
        "/api/v1/loans",
        json={"book_id": book_id, "branch_id": branch_id},
        headers=member_headers,
    )
    # La API debe rechazar por falta de copias; asumimos 400 (ajusta si usas 409)
    assert resp_loan2.status_code in (400, 409), resp_loan2.text


def test_member_cannot_cancel_after_approval(
    client: TestClient,
    admin_headers,
    member_headers,
):
    """
    Edge case:
    - Member pide préstamo (REQUESTED)
    - ADMIN lo aprueba (APPROVED)
    - Member intenta CANCELAR después de aprobado -> 403
    """
    branch_id = _create_branch(
        client,
        admin_headers,
        "Branch CancelAfterApproval",
        "branch_cancel_after@library.local",
    )

    book_id = _create_book_one_copy(
        client,
        admin_headers,
        branch_id,
        title="Libro CancelAfter",
        isbn_prefix="EDGE-CANCEL",
    )

    # Member crea préstamo
    resp_loan = client.post(
        "/api/v1/loans",
        json={"book_id": book_id, "branch_id": branch_id},
        headers=member_headers,
    )
    assert resp_loan.status_code == 201, resp_loan.text
    loan = resp_loan.json()

    # Admin aprueba
    resp_approve = client.patch(
        f"/api/v1/loans/{loan['id']}/status",
        json={"new_status": "APPROVED"},
        headers=admin_headers,
    )
    assert resp_approve.status_code == 200, resp_approve.text

    # Member intenta cancelar -> debe ser 403
    resp_cancel = client.patch(
        f"/api/v1/loans/{loan['id']}/status",
        json={"new_status": "CANCELED"},
        headers=member_headers,
    )
    assert resp_cancel.status_code == 403, resp_cancel.text


def test_admin_invalid_status_fails(
    client: TestClient,
    admin_headers,
    member_headers,
):
    """
    Edge case:
    - ADMIN intenta cambiar el estado a uno inválido (no definido en enum).
    - Debe devolver 422 (validación de Pydantic).
    """
    branch_id = _create_branch(
        client,
        admin_headers,
        "Branch InvalidStatus",
        "branch_invalid_status@library.local",
    )

    book_id = _create_book_one_copy(
        client,
        admin_headers,
        branch_id,
        title="Libro Invalid Status",
        isbn_prefix="EDGE-INVALID",
    )

    # Member crea préstamo (REQUESTED)
    resp_loan = client.post(
        "/api/v1/loans",
        json={"book_id": book_id, "branch_id": branch_id},
        headers=member_headers,
    )
    assert resp_loan.status_code == 201, resp_loan.text
    loan = resp_loan.json()

    # Admin intenta pasar un valor inválido en el body
    resp_invalid = client.patch(
        f"/api/v1/loans/{loan['id']}/status",
        json={"new_status": "NOT_A_VALID_STATUS"},
        headers=admin_headers,
    )
    assert resp_invalid.status_code == 422, resp_invalid.text
