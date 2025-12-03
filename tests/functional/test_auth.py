from fastapi.testclient import TestClient


def test_admin_login_success(client: TestClient):
    resp = client.post(
        "/api/v1/auth/login",
        data={"username": "admin@library.local", "password": "admin123"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_fail_wrong_password(client: TestClient):
    resp = client.post(
        "/api/v1/auth/login",
        data={"username": "admin@library.local", "password": "wrong"},
    )
    assert resp.status_code == 401
