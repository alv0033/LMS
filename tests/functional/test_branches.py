from fastapi.testclient import TestClient


#Falta aclarar para que es cada test

# ============================================================
# YA EXISTENTES (NO SE MODIFICAN)
# ============================================================

def test_create_branch_as_admin(client: TestClient, admin_headers):
    payload = {
        "name": "Sucursal Test",
        "address": "Calle Falsa 123",
        "description": "Sucursal de pruebas",
        "phone_number": "555-000-0000",
        "email": "branch_test@library.local",
        "is_active": True,
    }
    resp = client.post("/api/v1/branches", json=payload, headers=admin_headers)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["name"] == payload["name"]
    assert "id" in data


def test_list_branches_requires_auth(client: TestClient):
    resp = client.get("/api/v1/branches")
    assert resp.status_code in (401, 403)


def test_list_branches_as_admin(client: TestClient, admin_headers):
    resp = client.get("/api/v1/branches", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)



def test_list_branches_as_member(client: TestClient, member_headers):
    resp = client.get("/api/v1/branches", headers=member_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_create_branch_as_librarian(client: TestClient, librarian_headers):
    payload = {
        "name": "Sucursal Librarian",
        "address": "Calle Librarian",
        "description": "Creada por librarian",
        "phone_number": "555-111-1111",
        "email": "branch_librarian@library.local",
        "is_active": True,
    }
    resp = client.post("/api/v1/branches", json=payload, headers=librarian_headers)
    assert resp.status_code == 201


def test_member_cannot_create_branch(client: TestClient, member_headers):
    payload = {
        "name": "Sucursal Blocked",
        "address": "Fake",
        "description": "No debería permitirse",
        "phone_number": "555-000-2222",
        "email": "branch_blocked@library.local",
        "is_active": True,
    }
    resp = client.post("/api/v1/branches", json=payload, headers=member_headers)
    assert resp.status_code == 403


def test_get_branch_by_id(client: TestClient, admin_headers):
    payload = {
        "name": "Sucursal Get",
        "address": "Calle X",
        "description": "Get detail",
        "phone_number": "555-888-7777",
        "email": "branch_get@library.local",
        "is_active": True,
    }
    created = client.post("/api/v1/branches", json=payload, headers=admin_headers).json()
    branch_id = created["id"]

    resp = client.get(f"/api/v1/branches/{branch_id}", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == branch_id


def test_update_branch_as_admin(client: TestClient, admin_headers):
    # 1) Crear la sucursal
    resp_create = client.post(
        "/api/v1/branches",
        json={
            "name": "Sucursal Upd",
            "address": "Calle Upd",
            "description": "Para actualizar",
            "phone_number": "555-000-1111",
            "email": "branch_upd@library.com",
            "is_active": True,
        },
        headers=admin_headers,
    )
    assert resp_create.status_code == 201, resp_create.text
    branch_id = resp_create.json()["id"]

    # 2) Obtener el estado actual para conocer el esquema exacto
    resp_get = client.get(f"/api/v1/branches/{branch_id}", headers=admin_headers)
    assert resp_get.status_code == 200, resp_get.text
    data = resp_get.json()

    # 3) Modificar solo algunos campos
    data["name"] = "Sucursal Upd 2"
    data["description"] = "Actualizada por admin"

    # 4) Enviar PUT con el mismo esquema que devuelve la API
    resp_update = client.put(
        f"/api/v1/branches/{branch_id}",
        json=data,
        headers=admin_headers,
    )
    assert resp_update.status_code == 200, resp_update.text
    updated = resp_update.json()
    assert updated["name"] == "Sucursal Upd 2"
    assert updated["description"] == "Actualizada por admin"


def test_update_branch_as_librarian(client: TestClient, librarian_headers, admin_headers):
    # 1) Admin crea la sucursal
    resp_create = client.post(
        "/api/v1/branches",
        json={
            "name": "Sucursal Upd L",
            "address": "Calle L",
            "description": "Para librarian",
            "phone_number": "555-321-3210",
            "email": "branch_upd_l@library.com",
            "is_active": True,
        },
        headers=admin_headers,
    )
    assert resp_create.status_code == 201, resp_create.text
    branch_id = resp_create.json()["id"]

    # 2) Librarian hace GET para obtener el JSON exacto
    resp_get = client.get(f"/api/v1/branches/{branch_id}", headers=librarian_headers)
    assert resp_get.status_code == 200, resp_get.text
    data = resp_get.json()

    # 3) Librarian modifica solo algunos campos
    data["description"] = "Editada por librarian"

    # 4) Librarian envía el PUT
    resp_update = client.put(
        f"/api/v1/branches/{branch_id}",
        json=data,
        headers=librarian_headers,
    )
    assert resp_update.status_code == 200, resp_update.text
    updated = resp_update.json()
    assert updated["description"] == "Editada por librarian"


def test_member_cannot_update_branch(client: TestClient, member_headers, admin_headers):
    created = client.post(
        "/api/v1/branches",
        json={
            "name": "Sucursal No Update",
            "address": "Calle Block",
            "description": "Test",
            "phone_number": "555-111-0000",
            "email": "branch_no_upd@library.local",
            "is_active": True,
        },
        headers=admin_headers,
    ).json()

    branch_id = created["id"]

    resp = client.put(
        f"/api/v1/branches/{branch_id}",
        json={
            "name": "Intento ilegal",
            "address": "N/A",
            "description": "N/A",
            "phone_number": "0",
            "email": "x@x.com",
            "is_active": True,
        },
        headers=member_headers,
    )
    assert resp.status_code == 403


def test_delete_branch_as_admin(client: TestClient, admin_headers):
    created = client.post(
        "/api/v1/branches",
        json={
            "name": "Sucursal Delete",
            "address": "Calle Delete",
            "description": "A borrar",
            "phone_number": "555-444-3333",
            "email": "branch_delete@library.local",
            "is_active": True,
        },
        headers=admin_headers,
    ).json()
    branch_id = created["id"]

    resp = client.delete(f"/api/v1/branches/{branch_id}", headers=admin_headers)
    assert resp.status_code == 204


def test_librarian_cannot_delete_branch(client: TestClient, librarian_headers, admin_headers):
    created = client.post(
        "/api/v1/branches",
        json={
            "name": "Sucursal No Delete L",
            "address": "Calle NoDel",
            "description": "Test",
            "phone_number": "555-5656",
            "email": "branch_nodel_l@library.local",
            "is_active": True,
        },
        headers=admin_headers,
    ).json()
    branch_id = created["id"]

    resp = client.delete(f"/api/v1/branches/{branch_id}", headers=librarian_headers)
    assert resp.status_code == 403


def test_member_cannot_delete_branch(client: TestClient, member_headers, admin_headers):
    created = client.post(
        "/api/v1/branches",
        json={
            "name": "Sucursal No Delete M",
            "address": "Calle NoDel M",
            "description": "Test",
            "phone_number": "555-9999",
            "email": "branch_nodel_m@library.local",
            "is_active": True,
        },
        headers=admin_headers,
    ).json()
    branch_id = created["id"]

    resp = client.delete(f"/api/v1/branches/{branch_id}", headers=member_headers)
    assert resp.status_code == 403

from fastapi.testclient import TestClient


def test_inactive_branch_created_correctly(client: TestClient, admin_headers):
    # Crear active + inactive
    resp_active = client.post(
        "/api/v1/branches",
        json={
            "name": "Active Branch",
            "address": "A1",
            "description": "Activa",
            "phone_number": "555-111",
            "email": "active_branch@library.com",
            "is_active": True,
        },
        headers=admin_headers,
    )
    assert resp_active.status_code == 201, resp_active.text

    resp_inactive = client.post(
        "/api/v1/branches",
        json={
            "name": "Inactive Branch",
            "address": "I1",
            "description": "Inactiva",
            "phone_number": "555-222",
            "email": "inactive_branch@library.com",
            "is_active": False,
        },
        headers=admin_headers,
    )
    assert resp_inactive.status_code == 201, resp_inactive.text

    # Solo verificamos que ambas existen en el listado
    resp_list = client.get("/api/v1/branches", headers=admin_headers)
    assert resp_list.status_code == 200, resp_list.text
    names = [b["name"] for b in resp_list.json()]

    assert "Active Branch" in names
    assert "Inactive Branch" in names
