def create_project(client, headers, name="Invite Test Project"):
    response = client.post(
        "/projects",
        json={"name": name, "description": "for invite tests"},
        headers=headers,
    )
    return response.json()["id"]


def test_invite_requires_owner(
    client, auth_headers, second_user_headers, second_username
):
    project_id = create_project(client, auth_headers)
    response = client.post(
        f"/project/{project_id}/invite?user={second_username}&role=viewer",
        headers=second_user_headers,
    )
    assert response.status_code == 403


def test_invite_nonexistent_user(client, auth_headers):
    project_id = create_project(client, auth_headers)
    response = client.post(
        f"/project/{project_id}/invite?user=ghost&role=editor", headers=auth_headers
    )
    assert response.status_code == 404


def test_invite_success_as_editor(client, auth_headers, second_username):
    project_id = create_project(client, auth_headers)
    response = client.post(
        f"/project/{project_id}/invite?user={second_username}&role=editor",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["role"] == "editor"


def test_invite_success_as_viewer(client, auth_headers, second_username):
    project_id = create_project(client, auth_headers)
    response = client.post(
        f"/project/{project_id}/invite?user={second_username}&role=viewer",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["role"] == "viewer"


def test_invite_rejects_owner_role(client, auth_headers, second_username):
    project_id = create_project(client, auth_headers)
    response = client.post(
        f"/project/{project_id}/invite?user={second_username}&role=owner",
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_invited_user_can_access_project(
    client, auth_headers, second_user_headers, second_username
):
    project_id = create_project(client, auth_headers)
    client.post(
        f"/project/{project_id}/invite?user={second_username}&role=editor",
        headers=auth_headers,
    )

    response = client.get(f"/project/{project_id}/info", headers=second_user_headers)
    assert response.status_code == 200


def test_reinviting_updates_existing_role(client, auth_headers, second_username):
    project_id = create_project(client, auth_headers)
    client.post(
        f"/project/{project_id}/invite?user={second_username}&role=viewer",
        headers=auth_headers,
    )

    response = client.post(
        f"/project/{project_id}/invite?user={second_username}&role=editor",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["role"] == "editor"


def test_invite_to_nonexistent_project(client, auth_headers, second_username):
    response = client.post(
        f"/project/999/invite?user={second_username}&role=editor", headers=auth_headers
    )
    assert response.status_code == 404
