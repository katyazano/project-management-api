def test_create_project_requires_auth(client):
    response = client.post("/projects", json={"name": "No Auth", "description": "test"})
    assert response.status_code == 401


def test_create_project_success(client, auth_headers):
    response = client.post(
        "/projects",
        json={"name": "Test Project", "description": "A project"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Project"
    assert data["description"] == "A project"
    assert "id" in data


def test_get_projects_only_shows_own(client, auth_headers):
    client.post(
        "/projects", json={"name": "Mine", "description": "test"}, headers=auth_headers
    )
    other_user = {
        "username": "otheruser",
        "email": "otheruser@example.com",
        "password": "SecurePass1!",
        "repeat_password": "SecurePass1!",
    }
    client.post("/auth", json=other_user)
    login = client.post(
        "/login",
        data={"username": other_user["username"], "password": other_user["password"]},
    )
    other_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    response = client.get("/projects", headers=other_headers)
    assert response.status_code == 200
    assert response.json() == []


def test_get_project_info_not_found(client, auth_headers):
    response = client.get("/project/999/info", headers=auth_headers)
    assert response.status_code == 404


def test_get_project_info_success(client, auth_headers):
    create = client.post(
        "/projects", json={"name": "Test", "description": "test"}, headers=auth_headers
    )
    project_id = create.json()["id"]
    response = client.get(f"/project/{project_id}/info", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["id"] == project_id


def test_update_project_requires_both_fields(client, auth_headers):
    create = client.post(
        "/projects", json={"name": "Test", "description": "test"}, headers=auth_headers
    )
    project_id = create.json()["id"]
    response = client.put(
        f"/project/{project_id}/info", json={"name": "New Name"}, headers=auth_headers
    )
    assert response.status_code == 422


def test_update_project_success(client, auth_headers):
    create = client.post(
        "/projects", json={"name": "Test", "description": "test"}, headers=auth_headers
    )
    project_id = create.json()["id"]
    response = client.put(
        f"/project/{project_id}/info",
        json={"name": "New Name", "description": "New Description"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["name"] == "New Name"
    assert response.json()["description"] == "New Description"


def test_delete_project_success(client, auth_headers):
    create = client.post(
        "/projects", json={"name": "Test", "description": "test"}, headers=auth_headers
    )
    project_id = create.json()["id"]
    response = client.delete(f"/project/{project_id}", headers=auth_headers)
    assert response.status_code == 204

    response = client.get(f"/project/{project_id}/info", headers=auth_headers)
    assert response.status_code == 404
