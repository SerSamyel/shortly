from tests.conftest import signup


async def test_signup_returns_token_and_user(client):
    response = await client.post(
        "/api/auth/signup", json={"email": "New@Example.com", "password": "long-enough"}
    )
    assert response.status_code == 201
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"]["email"] == "new@example.com"
    assert "password" not in str(body)


async def test_duplicate_email_is_rejected_case_insensitively(client):
    await signup(client, "dup@example.com")
    response = await client.post(
        "/api/auth/signup", json={"email": "DUP@example.com", "password": "long-enough"}
    )
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


async def test_short_password_is_a_validation_error(client):
    response = await client.post(
        "/api/auth/signup", json={"email": "a@example.com", "password": "short"}
    )
    assert response.status_code == 422
    body = response.json()
    assert body["errors"][0]["field"] == "password"
    assert body["detail"] == body["errors"][0]["message"]


async def test_invalid_email_is_a_validation_error(client):
    response = await client.post(
        "/api/auth/signup", json={"email": "not-an-email", "password": "long-enough"}
    )
    assert response.status_code == 422
    assert response.json()["errors"][0]["field"] == "email"


async def test_login_with_correct_password(client):
    await signup(client, "login@example.com")
    response = await client.post(
        "/api/auth/login", json={"email": "login@example.com", "password": "correct-horse"}
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    me = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "login@example.com"


async def test_login_with_wrong_password_or_unknown_email_is_401(client):
    await signup(client, "login@example.com")
    wrong = await client.post(
        "/api/auth/login", json={"email": "login@example.com", "password": "wrong-password"}
    )
    unknown = await client.post(
        "/api/auth/login", json={"email": "nobody@example.com", "password": "wrong-password"}
    )
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json()["detail"] == unknown.json()["detail"] == "Wrong email or password"


async def test_protected_endpoints_need_a_valid_token(client):
    assert (await client.get("/api/links")).status_code == 401
    bad = await client.get("/api/links", headers={"Authorization": "Bearer nonsense"})
    assert bad.status_code == 401
    assert bad.json() == {"detail": "Not authenticated"}
