import uuid
from typing import Dict
from fastapi.testclient import TestClient

import logging

logger = logging.getLogger("api.branches")


def _unique_isbn(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


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


def test_logging_branch_create(
    client: TestClient,
    admin_headers,
    capsys,
):
    """
    Verifica que al crear una sucursal se genere un log con operation=branch_create.
    """
    _ = _create_branch(
        client,
        admin_headers,
        "Branch Logging",
        "branch_logging@library.local",
    )

    captured = capsys.readouterr()
    stdout = captured.out

    assert "operation" in stdout
    assert "branch_create" in stdout


def test_logging_loan_status_change(
    client: TestClient,
    admin_headers,
    member_headers,
    capsys,
):
    """
    Verifica que al cambiar el estado de un préstamo
    se loguee operation=loan_status_change y los estados old/new en mayúsculas.
    """
    branch = _create_branch(
        client,
        admin_headers,
        "Branch LoanLog",
        "branch_loanlog@library.local",
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

    captured = capsys.readouterr()
    stdout = captured.out

    # buscaremos operation=loan_status_change y estados en mayúsculas
    assert "loan_status_change" in stdout
    assert "REQUESTED" in stdout
    assert "APPROVED" in stdout
