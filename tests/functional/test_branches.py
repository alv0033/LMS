from fastapi.testclient import TestClient


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
    # depende de cómo tienes configurado get_current_user, normalmente 401
    assert resp.status_code in (401, 403)


def test_list_branches_as_admin(client: TestClient, admin_headers):
    resp = client.get("/api/v1/branches", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
