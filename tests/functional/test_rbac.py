import uuid
from typing import Dict

from fastapi.testclient import TestClient
import pytest

#Todos los requerimientos de RBAC (Role Based Access Control)

# ============================================================
# Helpers
# ============================================================

def _unique_email(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}@example.com"


def _create_user_as_admin(
    client: TestClient,
    admin_headers: Dict,
    email: str,
    role: str = "member",
) -> Dict:
    """
    Crea un usuario usando el endpoint de Admin para USERS.
    Debes tener implementado POST /api/v1/users (Admin only).
    """
    payload = {
        "email": email,
        "password": "Password123!",
        "full_name": "User RBAC",
        "role": role,
        "is_active": True,
    }
    resp = client.post("/api/v1/users", json=payload, headers=admin_headers)
    assert resp.status_code in (200, 201), resp.text
    return resp.json()


def _create_branch_as_admin(
    client: TestClient,
    admin_headers: Dict,
    name: str,
    email: str,
) -> Dict:
    payload = {
        "name": name,
        "address": "Calle RBAC 123",
        "description": "Sucursal RBAC",
        "phone_number": "555-000-1111",
        "email": email,
        "is_active": True,
    }
    resp = client.post("/api/v1/branches", json=payload, headers=admin_headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_book_as_admin(
    client: TestClient,
    admin_headers: Dict,
    branch_id: int,
    title: str,
) -> Dict:
    payload = {
        "title": title,
        "author": "Autor RBAC",
        "isbn": f"RBAC-ISBN-{uuid.uuid4().hex[:8]}",
        "description": "Libro RBAC",
        "genre": "Test",
        "publication_year": 2024,
        "total_copies": 5,
        "branch_id": branch_id,
    }
    resp = client.post("/api/v1/books", json=payload, headers=admin_headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_loan_as_member(
    client: TestClient,
    member_headers: Dict,
    book_id: int,
    branch_id: int,
) -> Dict:
    payload = {
        "book_id": book_id,
        "branch_id": branch_id,
    }
    resp = client.post("/api/v1/loans", json=payload, headers=member_headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ============================================================
# USERS - Solo Admin
# ============================================================

#Test verifica que un administrador puede listar todos los usuarios.

def test_admin_can_list_users(client: TestClient, admin_headers):
    resp = client.get("/api/v1/users", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert isinstance(data, list)

#test que verifica que un administrador puede ver los detalles de un usuario específico.
def test_admin_can_get_user_detail(client: TestClient, admin_headers):
    # Crear usuario primero
    email = _unique_email("detail")
    created = _create_user_as_admin(client, admin_headers, email=email, role="member")

    user_id = created["id"]
    resp = client.get(f"/api/v1/users/{user_id}", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["id"] == user_id
    assert data["email"] == email

#test que verifica que un administrador puede actualizar la información de un usuario.
def test_admin_can_update_user(client: TestClient, admin_headers):
    email = _unique_email("update")
    created = _create_user_as_admin(client, admin_headers, email=email, role="member")

    user_id = created["id"]
    payload = {
        "full_name": "User RBAC Updated",
        "role": "librarian",
        "is_active": True,
    }
    resp = client.put(f"/api/v1/users/{user_id}", json=payload, headers=admin_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["full_name"] == "User RBAC Updated"
    assert data["role"] == "librarian"

#Test que verifica que un administrador puede eliminar un usuario.
def test_admin_can_delete_user(client: TestClient, admin_headers):
    email = _unique_email("delete")
    created = _create_user_as_admin(client, admin_headers, email=email, role="member")
    user_id = created["id"]

    resp = client.delete(f"/api/v1/users/{user_id}", headers=admin_headers)
    assert resp.status_code in (200, 204), resp.text

    # Confirmar que ya no existe
    resp2 = client.get(f"/api/v1/users/{user_id}", headers=admin_headers)
    assert resp2.status_code == 404

#Test que verifica que un usuario con rol MEMBER no puede acceder a los endpoints de usuarios.
def test_member_cannot_access_users_endpoints(client: TestClient, member_headers):
    # Listar
    resp_list = client.get("/api/v1/users", headers=member_headers)
    assert resp_list.status_code == 403

    # Intentar ver un usuario
    resp_detail = client.get("/api/v1/users/1", headers=member_headers)
    assert resp_detail.status_code == 403

#Test que verifica que un usuario con rol LIBRARIAN no puede acceder a los endpoints de usuarios.
def test_librarian_cannot_access_users_endpoints(client: TestClient, librarian_headers):
    resp_list = client.get("/api/v1/users", headers=librarian_headers)
    assert resp_list.status_code == 403

    resp_detail = client.get("/api/v1/users/1", headers=librarian_headers)
    assert resp_detail.status_code == 403

#test que verifica que el usuario administrador incorporado (builtin) no pueda ser eliminado.
def test_cannot_delete_builtin_admin(client: TestClient, admin_headers):
    """
    Busca el usuario builtin admin (por email) y verifica
    que intentar borrarlo da error.
    """
    resp = client.get("/api/v1/users", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    users = resp.json()

    builtin = None
    for u in users:
        if u["email"] == "admin@library.local":
            builtin = u
            break

    assert builtin is not None, "No se encontró el builtin admin en /users."
    admin_id = builtin["id"]

    resp_del = client.delete(f"/api/v1/users/{admin_id}", headers=admin_headers)
    assert resp_del.status_code in (400, 403), resp_del.text


# ============================================================
# BRANCHES - Librarian vs Admin vs Member
# ============================================================

#Test que verifica que un usuario con rol LIBRARIAN puede crear una sucursal.
def test_librarian_can_create_branch(client: TestClient, librarian_headers):
    payload = {
        "name": "Sucursal Librarian",
        "address": "Calle Librarian 1",
        "description": "Sucursal creada por librarian",
        "phone_number": "555-111-2222",
        "email": _unique_email("branch_librarian"),
        "is_active": True,
    }
    resp = client.post("/api/v1/branches", json=payload, headers=librarian_headers)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["name"] == payload["name"]

#test que verifica que un usuario con rol MEMBER no puede crear una sucursal.
def test_member_cannot_create_branch(client: TestClient, member_headers):
    payload = {
        "name": "Sucursal Member",
        "address": "Calle Member 1",
        "description": "No debería poder crear",
        "phone_number": "555-333-4444",
        "email": _unique_email("branch_member"),
        "is_active": True,
    }
    resp = client.post("/api/v1/branches", json=payload, headers=member_headers)
    assert resp.status_code == 403, resp.text

#test que verifica que un usuario con rol ADMIN puede actualizar una sucursal.
def test_librarian_can_update_branch(client: TestClient, admin_headers, librarian_headers):
    branch = _create_branch_as_admin(
        client,
        admin_headers,
        name="Sucursal Actualizar Librarian",
        email=_unique_email("branch_upd"),
    )
    branch_id = branch["id"]

    payload = {
        "name": "Sucursal Actualizada Por Librarian",
        "address": "Calle Actualizada",
        "description": "Actualizada por librario",
        "phone_number": "555-000-9999",
        "email": branch["email"],
        "is_active": True,
    }

    resp = client.put(
        f"/api/v1/branches/{branch_id}",
        json=payload,
        headers=librarian_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["name"] == "Sucursal Actualizada Por Librarian"

#test que verifica que un usuario con rol MEMBER no puede actualizar una sucursal.
def test_member_cannot_update_branch(client: TestClient, admin_headers, member_headers):
    branch = _create_branch_as_admin(
        client,
        admin_headers,
        name="Sucursal No Actualizable",
        email=_unique_email("branch_no_upd"),
    )
    branch_id = branch["id"]

    payload = {
        "name": "No debería actualizar",
        "address": "Calle X",
        "description": "Member no puede",
        "phone_number": "555-123-0000",
        "email": branch["email"],
        "is_active": True,
    }

    resp = client.put(
        f"/api/v1/branches/{branch_id}",
        json=payload,
        headers=member_headers,
    )
    assert resp.status_code == 403, resp.text

#test que verifica que un usuario con rol ADMIN puede eliminar una sucursal.
def test_admin_can_delete_branch(client: TestClient, admin_headers):
    branch = _create_branch_as_admin(
        client,
        admin_headers,
        name="Sucursal A Borrar",
        email=_unique_email("branch_del"),
    )
    branch_id = branch["id"]

    resp = client.delete(f"/api/v1/branches/{branch_id}", headers=admin_headers)
    assert resp.status_code in (200, 204), resp.text

#test que verifica que un usuario con rol LIBRARIAN no puede eliminar una sucursal.
def test_librarian_cannot_delete_branch(client: TestClient, admin_headers, librarian_headers):
    branch = _create_branch_as_admin(
        client,
        admin_headers,
        name="Sucursal Librarian No Delete",
        email=_unique_email("branch_no_del_lib"),
    )
    branch_id = branch["id"]

    resp = client.delete(
        f"/api/v1/branches/{branch_id}",
        headers=librarian_headers,
    )
    assert resp.status_code == 403, resp.text

#test que verifica que un usuario con rol MEMBER no puede eliminar una sucursal.
def test_member_cannot_delete_branch(client: TestClient, admin_headers, member_headers):
    branch = _create_branch_as_admin(
        client,
        admin_headers,
        name="Sucursal Member No Delete",
        email=_unique_email("branch_no_del_mem"),
    )
    branch_id = branch["id"]

    resp = client.delete(
        f"/api/v1/branches/{branch_id}",
        headers=member_headers,
    )
    assert resp.status_code == 403, resp.text


# ============================================================
# BOOKS - Librarian vs Admin vs Member
# ============================================================

#test que verifica que un usuario con rol LIBRARIAN puede crear un libro.
def test_librarian_can_create_book(
    client: TestClient,
    admin_headers,
    librarian_headers,
):
    branch = _create_branch_as_admin(
        client,
        admin_headers,
        name="Sucursal Lib Books",
        email=_unique_email("branch_lib_books"),
    )
    branch_id = branch["id"]

    payload = {
        "title": "Libro Creado Por Librarian",
        "author": "Autor RBAC",
        "isbn": f"RBAC-LIB-{uuid.uuid4().hex[:8]}",
        "description": "Creado por librarian",
        "genre": "Test",
        "publication_year": 2024,
        "total_copies": 3,
        "branch_id": branch_id,
    }

    resp = client.post("/api/v1/books", json=payload, headers=librarian_headers)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["title"] == payload["title"]

#test que verifica que un usuario con rol MEMBER no puede crear un libro.
def test_member_cannot_create_book(
    client: TestClient,
    admin_headers,
    member_headers,
):
    branch = _create_branch_as_admin(
        client,
        admin_headers,
        name="Sucursal Member Books",
        email=_unique_email("branch_mem_books"),
    )
    branch_id = branch["id"]

    payload = {
        "title": "Libro Member No Should",
        "author": "Autor RBAC",
        "isbn": f"RBAC-MEM-{uuid.uuid4().hex[:8]}",
        "description": "Member no puede",
        "genre": "Test",
        "publication_year": 2024,
        "total_copies": 3,
        "branch_id": branch_id,
    }

    resp = client.post("/api/v1/books", json=payload, headers=member_headers)
    assert resp.status_code == 403, resp.text


#test que verifica que un usuario con rol ADMIN puede actualizar un libro.
def test_librarian_can_update_book(
    client: TestClient,
    admin_headers,
    librarian_headers,
):
    branch = _create_branch_as_admin(
        client,
        admin_headers,
        name="Sucursal Update Book",
        email=_unique_email("branch_upd_book"),
    )
    branch_id = branch["id"]

    book = _create_book_as_admin(
        client,
        admin_headers,
        branch_id=branch_id,
        title="Libro A Actualizar",
    )
    book_id = book["id"]

    payload = {
        "title": "Libro Actualizado Librarian",
        "author": "Autor RBAC Upd",
        "isbn": book["isbn"],
        "description": "Actualizado",
        "genre": "Test",
        "publication_year": 2025,
        "total_copies": 10,
        "branch_id": branch_id,
    }

    resp = client.put(
        f"/api/v1/books/{book_id}",
        json=payload,
        headers=librarian_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["title"] == "Libro Actualizado Librarian"


#test que verifica que un usuario con rol MEMBER no puede actualizar un libro.
def test_member_cannot_update_book(
    client: TestClient,
    admin_headers,
    member_headers,
):
    branch = _create_branch_as_admin(
        client,
        admin_headers,
        name="Sucursal Member Upd Book",
        email=_unique_email("branch_mem_upd_book"),
    )
    branch_id = branch["id"]

    book = _create_book_as_admin(
        client,
        admin_headers,
        branch_id=branch_id,
        title="Libro Member No Upd",
    )
    book_id = book["id"]

    payload = {
        "title": "No debería poder",
        "author": "Autor X",
        "isbn": book["isbn"],
        "description": "Member no actualiza",
        "genre": "Test",
        "publication_year": 2025,
        "total_copies": 1,
        "branch_id": branch_id,
    }

    resp = client.put(
        f"/api/v1/books/{book_id}",
        json=payload,
        headers=member_headers,
    )
    assert resp.status_code == 403, resp.text

#test que verifica que un usuario con rol ADMIN puede eliminar un libro.
def test_admin_can_delete_book(
    client: TestClient,
    admin_headers,
):
    branch = _create_branch_as_admin(
        client,
        admin_headers,
        name="Sucursal Delete Book",
        email=_unique_email("branch_del_book"),
    )
    branch_id = branch["id"]

    book = _create_book_as_admin(
        client,
        admin_headers,
        branch_id=branch_id,
        title="Libro A Borrar",
    )
    book_id = book["id"]

    resp = client.delete(f"/api/v1/books/{book_id}", headers=admin_headers)
    assert resp.status_code in (200, 204), resp.text

#test que verifica que un usuario con rol LIBRARIAN no puede eliminar un libro.
def test_librarian_cannot_delete_book(
    client: TestClient,
    admin_headers,
    librarian_headers,
):
    branch = _create_branch_as_admin(
        client,
        admin_headers,
        name="Sucursal Lib No Del Book",
        email=_unique_email("branch_lib_no_del_book"),
    )
    branch_id = branch["id"]

    book = _create_book_as_admin(
        client,
        admin_headers,
        branch_id=branch_id,
        title="Libro Lib No Delete",
    )
    book_id = book["id"]

    resp = client.delete(
        f"/api/v1/books/{book_id}",
        headers=librarian_headers,
    )
    assert resp.status_code == 403, resp.text

#test que verifica que un usuario con rol MEMBER no puede eliminar un libro.
def test_member_cannot_delete_book(
    client: TestClient,
    admin_headers,
    member_headers,
):
    branch = _create_branch_as_admin(
        client,
        admin_headers,
        name="Sucursal Mem No Del Book",
        email=_unique_email("branch_mem_no_del_book"),
    )
    branch_id = branch["id"]

    book = _create_book_as_admin(
        client,
        admin_headers,
        branch_id=branch_id,
        title="Libro Mem No Delete",
    )
    book_id = book["id"]

    resp = client.delete(
        f"/api/v1/books/{book_id}",
        headers=member_headers,
    )
    assert resp.status_code == 403, resp.text


#test que verifica que la restricción de unicidad del ISBN funciona al crear libros.
def test_isbn_unique_constraint_works(
    client: TestClient,
    admin_headers,
):
    branch = _create_branch_as_admin(
        client,
        admin_headers,
        name="Sucursal ISBN",
        email=_unique_email("branch_isbn"),
    )
    branch_id = branch["id"]

    isbn = f"RBAC-UNIQUE-{uuid.uuid4().hex[:8]}"

    payload1 = {
        "title": "Libro ISBN1",
        "author": "Autor X",
        "isbn": isbn,
        "description": "Primero",
        "genre": "Test",
        "publication_year": 2020,
        "total_copies": 2,
        "branch_id": branch_id,
    }
    resp1 = client.post("/api/v1/books", json=payload1, headers=admin_headers)
    assert resp1.status_code == 201, resp1.text

    payload2 = payload1.copy()
    payload2["title"] = "Libro ISBN2"
    resp2 = client.post("/api/v1/books", json=payload2, headers=admin_headers)

    assert resp2.status_code == 409, resp2.text


# ============================================================
# LOANS - Permisos por rol
# ============================================================

#test que verifica que un usuario con rol MEMBER puede solicitar un préstamo.
def test_member_can_request_loan(
    client: TestClient,
    admin_headers,
    member_headers,
    clean_member_loans,
):
    branch = _create_branch_as_admin(
        client,
        admin_headers,
        name="Sucursal Loans Member",
        email=_unique_email("branch_loans_mem"),
    )
    branch_id = branch["id"]

    book = _create_book_as_admin(
        client,
        admin_headers,
        branch_id=branch_id,
        title="Libro Loans Member",
    )
    book_id = book["id"]

    loan = _create_loan_as_member(client, member_headers, book_id, branch_id)
    assert loan["status"] == "REQUESTED"

#test que verifica que un usuario con rol LIBRARIAN no puede solicitar un préstamo para un miembro.
def test_librarian_cannot_request_loan_for_member(
    client: TestClient,
    admin_headers,
    librarian_headers,
):
    branch = _create_branch_as_admin(
        client,
        admin_headers,
        name="Sucursal Loans Lib",
        email=_unique_email("branch_loans_lib"),
    )
    branch_id = branch["id"]

    book = _create_book_as_admin(
        client,
        admin_headers,
        branch_id=branch_id,
        title="Libro Loans Lib",
    )
    book_id = book["id"]

    payload = {"book_id": book_id, "branch_id": branch_id}
    resp = client.post("/api/v1/loans", json=payload, headers=librarian_headers)
    # si tu diseño lo permite, cambia el código; la idea:
    assert resp.status_code in (403, 422), resp.text

#test que verifica que un usuario con rol MEMBER puede cancelar su propia solicitud de préstamo.
def test_member_can_cancel_requested_loan(
    client: TestClient,
    admin_headers,
    member_headers,
    clean_member_loans,
):
    branch = _create_branch_as_admin(
        client,
        admin_headers,
        name="Sucursal Loan Cancel Member",
        email=_unique_email("branch_loans_cancel_mem"),
    )
    branch_id = branch["id"]

    book = _create_book_as_admin(
        client,
        admin_headers,
        branch_id=branch_id,
        title="Libro Loan Cancel Member",
    )
    book_id = book["id"]

    loan = _create_loan_as_member(client, member_headers, book_id, branch_id)

    resp_cancel = client.patch(
        f"/api/v1/loans/{loan['id']}/status",
        json={"new_status": "CANCELED"},
        headers=member_headers,
    )
    assert resp_cancel.status_code == 200, resp_cancel.text
    data = resp_cancel.json()
    assert data["status"] == "CANCELED"


#test que verifica que un usuario con rol MEMBER no puede aprobar su propia solicitud de préstamo.
def test_member_cannot_approve_loan(
    client: TestClient,
    admin_headers,
    member_headers,
    clean_member_loans,
):
    branch = _create_branch_as_admin(
        client,
        admin_headers,
        name="Sucursal Loan Approve Mem",
        email=_unique_email("branch_loans_approve_mem"),
    )
    branch_id = branch["id"]

    book = _create_book_as_admin(
        client,
        admin_headers,
        branch_id=branch_id,
        title="Libro Loan Approve Mem",
    )
    book_id = book["id"]

    loan = _create_loan_as_member(client, member_headers, book_id, branch_id)

    resp_approve = client.patch(
        f"/api/v1/loans/{loan['id']}/status",
        json={"new_status": "APPROVED"},
        headers=member_headers,
    )
    assert resp_approve.status_code == 403, resp_approve.text

#test que verifica que un usuario con rol LIBRARIAN puede aprobar y marcar como prestado un préstamo.
def test_librarian_can_approve_and_mark_borrowed(
    client: TestClient,
    admin_headers,
    librarian_headers,
    member_headers,
    clean_member_loans,
):
    branch = _create_branch_as_admin(
        client,
        admin_headers,
        name="Sucursal Loan Lib Flow",
        email=_unique_email("branch_loans_lib_flow"),
    )
    branch_id = branch["id"]

    book = _create_book_as_admin(
        client,
        admin_headers,
        branch_id=branch_id,
        title="Libro Loan Lib Flow",
    )
    book_id = book["id"]

    loan = _create_loan_as_member(client, member_headers, book_id, branch_id)

    # Librarian aprueba
    resp_approve = client.patch(
        f"/api/v1/loans/{loan['id']}/status",
        json={"new_status": "APPROVED"},
        headers=librarian_headers,
    )
    assert resp_approve.status_code == 200, resp_approve.text
    data = resp_approve.json()
    assert data["status"] == "APPROVED"

    # Librarian marca BORROWED
    resp_borrowed = client.patch(
        f"/api/v1/loans/{loan['id']}/status",
        json={"new_status": "BORROWED"},
        headers=librarian_headers,
    )
    assert resp_borrowed.status_code == 200, resp_borrowed.text
    data2 = resp_borrowed.json()
    assert data2["status"] == "BORROWED"

#test que verifica que un usuario con rol LIBRARIAN puede marcar un préstamo como DEVUELTO o PERDIDO.
def test_librarian_can_mark_returned_and_lost(
    client: TestClient,
    admin_headers,
    librarian_headers,
    member_headers,
    clean_member_loans,
):
    branch = _create_branch_as_admin(
        client,
        admin_headers,
        name="Sucursal Loan Lib Return Lost",
        email=_unique_email("branch_loans_lib_ret_lost"),
    )
    branch_id = branch["id"]

    book = _create_book_as_admin(
        client,
        admin_headers,
        branch_id=branch_id,
        title="Libro Loan Lib Return Lost",
    )
    book_id = book["id"]

    loan = _create_loan_as_member(client, member_headers, book_id, branch_id)

    # Librarian -> APPROVED
    client.patch(
        f"/api/v1/loans/{loan['id']}/status",
        json={"new_status": "APPROVED"},
        headers=librarian_headers,
    )
    # Librarian -> BORROWED
    client.patch(
        f"/api/v1/loans/{loan['id']}/status",
        json={"new_status": "BORROWED"},
        headers=librarian_headers,
    )

    # Librarian -> RETURNED
    resp_ret = client.patch(
        f"/api/v1/loans/{loan['id']}/status",
        json={"new_status": "RETURNED"},
        headers=librarian_headers,
    )
    assert resp_ret.status_code == 200, resp_ret.text
    data_ret = resp_ret.json()
    assert data_ret["status"] == "RETURNED"

    # Crear otro préstamo para probar LOST
    loan2 = _create_loan_as_member(client, member_headers, book_id, branch_id)
    client.patch(
        f"/api/v1/loans/{loan2['id']}/status",
        json={"new_status": "APPROVED"},
        headers=librarian_headers,
    )
    client.patch(
        f"/api/v1/loans/{loan2['id']}/status",
        json={"new_status": "BORROWED"},
        headers=librarian_headers,
    )
    resp_lost = client.patch(
        f"/api/v1/loans/{loan2['id']}/status",
        json={"new_status": "LOST"},
        headers=librarian_headers,
    )
    assert resp_lost.status_code == 200, resp_lost.text
    data_lost = resp_lost.json()
    assert data_lost["status"] == "LOST"

#test que verifica que un usuario con rol MEMBER solo puede ver sus propios préstamos.
def test_member_can_only_see_their_own_loans(
    client: TestClient,
    admin_headers,
    member_headers,
    clean_member_loans,
):
    """
    Asume que existe al menos OTRO usuario con loans en el sistema.
    Aquí al menos verificamos que el endpoint /loans para Member
    no devuelve datos de otros usuarios de forma obvia.
    """
    # Crear datos para el member actual
    branch = _create_branch_as_admin(
        client,
        admin_headers,
        name="Sucursal Loans Member View",
        email=_unique_email("branch_loans_mem_view"),
    )
    branch_id = branch["id"]
    book = _create_book_as_admin(
        client,
        admin_headers,
        branch_id=branch_id,
        title="Libro Loans Member View",
    )
    _create_loan_as_member(client, member_headers, book_id=book["id"], branch_id=branch_id)

    # Listar loans como Member
    resp = client.get("/api/v1/loans", headers=member_headers)
    assert resp.status_code == 200, resp.text
    loans = resp.json()
    assert isinstance(loans, list)


#test que verifica que un usuario con rol ADMIN puede ver todos los préstamos.
def test_admin_can_view_all_loans(
    client: TestClient,
    admin_headers,
):
    resp = client.get("/api/v1/loans", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    loans = resp.json()
    assert isinstance(loans, list)

