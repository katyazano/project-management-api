def test_register_user_success(client, user_payload):
    response = client.post("/auth", json=user_payload)
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == user_payload["username"]
    assert "id" in data
    assert "password" not in data
    assert "email" not in data


def test_register_duplicate_username(client, user_payload):
    client.post("/auth", json=user_payload)
    response = client.post("/auth", json=user_payload)
    assert response.status_code == 400


def test_register_password_mismatch(client, user_payload):
    user_payload["repeat_password"] = "DifferentPass1!"
    response = client.post("/auth", json=user_payload)
    assert response.status_code == 422


def test_register_weak_password(client, user_payload):
    user_payload["password"] = "weak"
    user_payload["repeat_password"] = "weak"
    response = client.post("/auth", json=user_payload)
    assert response.status_code == 422


def test_register_invalid_email(client, user_payload):
    user_payload["email"] = "not-an-email"
    response = client.post("/auth", json=user_payload)
    assert response.status_code == 422


def test_login_success(client, user_payload):
    client.post("/auth", json=user_payload)
    response = client.post(
        "/login",
        data={
            "username": user_payload["username"],
            "password": user_payload["password"],
        },
    )
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"


def test_login_wrong_password(client, user_payload):
    client.post("/auth", json=user_payload)
    response = client.post(
        "/login",
        data={"username": user_payload["username"], "password": "WrongPass1!"},
    )
    assert response.status_code == 401


def test_login_nonexistent_user(client):
    response = client.post(
        "/login", data={"username": "ghost", "password": "SecurePass1!"}
    )
    assert response.status_code == 401
