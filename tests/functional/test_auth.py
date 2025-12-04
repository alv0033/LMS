# se cubren 

from fastapi.testclient import TestClient

# Tests para el endpoint de login de autenticación (verifica login exitoso)
def test_admin_login_success(client: TestClient):
    resp = client.post(
        "/api/v1/auth/login",
        data={"username": "admin@library.local", "password": "admin123"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


# Tests para el endpoint de login de autenticación (verifica )
def test_login_fail_wrong_password(client: TestClient):
    resp = client.post(
        "/api/v1/auth/login",
        data={"username": "admin@library.local", "password": "wrong"},
    )
    assert resp.status_code == 401

#Test para  verificar que no puedes registrar dos usuarios con el mismo email 
#(correr dos veces si es el primer test)

def test_register_duplicate_email_fails(client: TestClient):
    email = "dup_user@example.com"

    payload = {
        "email": email,
        # usa una contraseña larga para evitar problemas de min_length
        "password": "Password123!",  # >= 8 caracteres
        "full_name": "User Dup",
        "role": "member",
        "is_active":  True,
        "is_blocked": False
    }

    # Primer registro
    resp1 = client.post("/api/v1/auth/register", json=payload)

    # mismo registro
    resp2 = client.post("/api/v1/auth/register", json=payload)
    assert resp2.status_code in (400, 409), resp2.text

   
#Test para  verificar formato de e mail

def test_register_invalid_email_fails(client: TestClient):
    payload = {
        "email": "correo-invalido",
        "password": "pass123",
        "full_name": "User Invalid",
        "role": "member",
    }

    resp = client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 422   # Pydantic validation error


#Test para verificar que no registrados no ingresan
def test_login_unregistered_email_fails(client: TestClient):
    resp = client.post(
        "/api/v1/auth/login",
        data={"username": "no_existe@example.com", "password": "pass123"},
    )
    assert resp.status_code == 401

#usuario bloqueado no puede ingresar
def test_login_blocked_user_fails(client: TestClient):

    #Agregado manualmente en la db= "blocked_user@example.com"

    # Intento de login
    resp = client.post(
        "/api/v1/auth/login",
        data={"username": "blocked_user@example.com", "password": "password123"},
    )
    assert resp.status_code in (401, 403), resp.text



# LOGOUT 

#Test para detectar tokens validados  despues de un log out
def test_logout_with_valid_token_succeeds(client: TestClient, member_headers):
    resp = client.post("/api/v1/auth/logout", headers=member_headers)
    assert resp.status_code in (200, 204)

    # Verificar que el mismo token ya no funciona
    resp2 = client.get("/api/v1/books", headers=member_headers)
    assert resp2.status_code in (401, 403)

#Test no se puede cerrar sesion sin token
def test_logout_without_token_fails(client: TestClient):
    resp = client.post("/api/v1/auth/logout")
    assert resp.status_code == 401



# PROTECCION DE ENDPOINTS

#Test no se puede acceder sin token a los endpoints 
def test_access_protected_endpoint_without_token_returns_401(client: TestClient):
    resp = client.get("/api/v1/books") #endpoint protegido
    assert resp.status_code in (401, 403)

#TEST que verifica que acceder a un endpoint con un token inválido devuelva un error 401, *asegurando que la autenticación rechace tokens no válidos)
def test_access_protected_endpoint_with_invalid_token_returns_401(client: TestClient):
    invalid_headers = {"Authorization": "Bearer INVALIDTOKEN123"}

    resp = client.get("/api/v1/books", headers=invalid_headers)
    assert resp.status_code in (401, 403)

# LOGGING 

#Test para verificar que hay un log por login exitoso
def test_auth_logging_login_success(client: TestClient, caplog):
    with caplog.at_level("INFO"):
        resp = client.post(
            "/api/v1/auth/login",
            data={"username": "admin@library.local", "password": "admin123"},
        )
        assert resp.status_code == 200

    # Buscar logs del login exitoso
    found = False
    for rec in caplog.records:
        if "login_success" in rec.message:
            found = True
            break

    assert found, "No se encontró log de login_success en caplog."

#test que verifica que hay un log por login fallido
def test_auth_logging_login_failure(client: TestClient, caplog):
    with caplog.at_level("WARNING"):
        resp = client.post(
            "/api/v1/auth/login",
            data={"username": "admin@library.local", "password": "wrong"},
        )
        assert resp.status_code == 401

    # Buscar logs de login_failed
    found = False
    for rec in caplog.records:
        if "login_failed" in rec.message or "invalid credentials" in rec.message:
            found = True
            break

    assert found, "No se encontró log de login_failed en caplog."