import uuid
from datetime import datetime, timedelta
from typing import Dict

from fastapi.testclient import TestClient


def _unique_isbn(prefix: str) -> str:
    """Genera un ISBN único por test para evitar choques con la BD."""
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _create_branch(client: TestClient, admin_headers: Dict, name: str, email: str) -> int:
    resp = client.post(
        "/api/v1/branches",
        json={
            "name": name,
            "address": "Calle Filtro 123",
            "description": "Sucursal para filtros",
            "phone_number": "555-123-9999",
            "email": email,
            "is_active": True,
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _create_book(
    client: TestClient,
    admin_headers: Dict,
    branch_id: int,
    title: str,
    isbn_prefix: str,
    author: str = "Autor Filtro",
) -> int:
    isbn = _unique_isbn(isbn_prefix)
    resp = client.post(
        "/api/v1/books",
        json={
            "title": title,
            "author": author,
            "isbn": isbn,
            "description": "Libro de prueba para filtros",
            "genre": "Test",
            "publication_year": 2020,
            "total_copies": 5,
            "branch_id": branch_id,
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _create_member_loan(
    client: TestClient,
    member_headers: Dict,
    book_id: int,
    branch_id: int,
) -> int:
    resp = client.post(
        "/api/v1/loans",
        json={
            "book_id": book_id,
            "branch_id": branch_id,
        },
        headers=member_headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def test_list_books_pagination(
    client: TestClient,
    admin_headers,
    member_headers,
):
    """
    Crea varios libros y verifica que la paginación
    con skip/limit funciona.
    """
    branch_id = _create_branch(
        client,
        admin_headers,
        name="Branch Paginación",
        email="branch_pagination@library.local",
    )

    # Creamos 25 libros
    for i in range(25):
        _create_book(
            client,
            admin_headers,
            branch_id,
            title=f"Libro Pag {i}",
            isbn_prefix="PAG-ISBN",
        )

    # Primer página: limit=10
    resp_page1 = client.get(
        "/api/v1/books?skip=0&limit=10",
        headers=member_headers,
    )
    assert resp_page1.status_code == 200, resp_page1.text
    data_page1 = resp_page1.json()
    assert len(data_page1) == 10

    # Segunda página: siguiente 10
    resp_page2 = client.get(
        "/api/v1/books?skip=10&limit=10",
        headers=member_headers,
    )
    assert resp_page2.status_code == 200, resp_page2.text
    data_page2 = resp_page2.json()
    assert len(data_page2) == 10

    # No deben repetir IDs entre página 1 y 2
    ids_page1 = {b["id"] for b in data_page1}
    ids_page2 = {b["id"] for b in data_page2}
    assert ids_page1.isdisjoint(ids_page2)


def test_list_books_filter_by_branch(
    client: TestClient,
    admin_headers,
    member_headers,
):
    """
    Crea dos sucursales y libros en cada una.
    Verifica filtrar libros por branch_id.
    """
    branch_a = _create_branch(
        client, admin_headers, "Branch A Filtro", "branch_a_filter@library.local"
    )
    branch_b = _create_branch(
        client, admin_headers, "Branch B Filtro", "branch_b_filter@library.local"
    )

    # Libros en A
    for i in range(3):
        _create_book(
            client,
            admin_headers,
            branch_a,
            title=f"Libro A {i}",
            isbn_prefix="FILTER-A",
        )

    # Libros en B
    for i in range(5):
        _create_book(
            client,
            admin_headers,
            branch_b,
            title=f"Libro B {i}",
            isbn_prefix="FILTER-B",
        )

    resp_a = client.get(
        f"/api/v1/books?branch_id={branch_a}",
        headers=member_headers,
    )
    assert resp_a.status_code == 200, resp_a.text
    data_a = resp_a.json()
    assert len(data_a) == 3
    assert all(b["branch_id"] == branch_a for b in data_a)

    resp_b = client.get(
        f"/api/v1/books?branch_id={branch_b}",
        headers=member_headers,
    )
    assert resp_b.status_code == 200, resp_b.text
    data_b = resp_b.json()
    assert len(data_b) == 5
    assert all(b["branch_id"] == branch_b for b in data_b)


def test_list_loans_filter_by_status(
    client: TestClient,
    admin_headers,
    member_headers,
):
    """
    Crea varios préstamos con distintos estados y verifica
    filtrado por status vía query param (si lo tienes)
    o, si no lo tienes, al menos que se pueda filtrar en memoria.
    """
    branch_id = _create_branch(
        client,
        admin_headers,
        "Branch LoansFilter",
        "branch_loansfilter@library.local",
    )

    # Creamos un libro
    book_id = _create_book(
        client,
        admin_headers,
        branch_id,
        title="Libro para LoansFilter",
        isbn_prefix="LOAN-FILTER",
    )

    # Creamos un préstamo REQUESTED
    loan_id = _create_member_loan(client, member_headers, book_id, branch_id)

    # Librarian / Admin aprueba el préstamo -> APPROVED
    resp_approve = client.patch(
        f"/api/v1/loans/{loan_id}/status",
        json={"new_status": "APPROVED"},
        headers=admin_headers,
    )
    assert resp_approve.status_code == 200, resp_approve.text

    # Si tienes endpoint con ?status=APPROVED, lo usas:
    resp = client.get("/api/v1/loans", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    loans = resp.json()

    approved = [l for l in loans if l["status"] == "APPROVED"]
    assert any(l["id"] == loan_id for l in approved)


def test_list_books_sort_by_title_asc_desc(
    client: TestClient,
    admin_headers,
    member_headers,
):
    """
    Verifica ordenamiento básico por título usando
    ?order_by=title&order_dir=asc|desc, filtrando por la sucursal
    creada en este test para evitar interferencia con otros datos.
    """
    branch_id = _create_branch(
        client,
        admin_headers,
        "Branch Sort",
        "branch_sort@library.local",
    )

    titles = ["ZZZ Libro", "MMM Libro", "AAA Libro"]
    for title in titles:
        _create_book(
            client,
            admin_headers,
            branch_id,
            title=title,
            isbn_prefix="SORT-ISBN",
        )

    # ASC: filtramos por branch y ponemos un limit alto
    resp_asc = client.get(
        f"/api/v1/books?branch_id={branch_id}&order_by=title&order_dir=asc&skip=0&limit=50",
        headers=member_headers,
    )
    assert resp_asc.status_code == 200, resp_asc.text
    data_asc = resp_asc.json()

    asc_titles = [b["title"] for b in data_asc]
    # primero aseguramos que estén los 3 títulos
    for t in titles:
        assert t in asc_titles

    # nos quedamos solo con los 3 en el orden recibido
    asc_subset = [t for t in asc_titles if t in titles]

    assert asc_subset.index("AAA Libro") < asc_subset.index("ZZZ Libro")

    # DESC
    resp_desc = client.get(
        f"/api/v1/books?branch_id={branch_id}&order_by=title&order_dir=desc&skip=0&limit=50",
        headers=member_headers,
    )
    assert resp_desc.status_code == 200, resp_desc.text
    data_desc = resp_desc.json()

    desc_titles = [b["title"] for b in data_desc]
    for t in titles:
        assert t in desc_titles

    desc_subset = [t for t in desc_titles if t in titles]

    assert desc_subset.index("ZZZ Libro") < desc_subset.index("AAA Libro")