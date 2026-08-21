from unittest.mock import patch

from app import security


def create_project(client, headers, name="Share Test Project"):
    response = client.post(
        "/projects",
        json={"name": name, "description": "for share tests"},
        headers=headers,
    )
    return response.json()["id"]


@patch("app.email.send_share_invite_email")
def test_share_requires_owner(mock_send, client, auth_headers, second_user_headers):
    project_id = create_project(client, auth_headers)
    response = client.get(
        f"/project/{project_id}/share?with=someone@example.com",
        headers=second_user_headers,
    )
    assert response.status_code == 403
    mock_send.assert_not_called()


@patch("app.email.send_share_invite_email")
def test_share_returns_join_link(mock_send, client, auth_headers):
    project_id = create_project(client, auth_headers)
    response = client.get(
        f"/project/{project_id}/share?with=invitee@example.com", headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "join_link" in data
    assert "/join?token=" in data["join_link"]
    assert data["expires_in_hours"] == 48
    mock_send.assert_called_once()


@patch("app.email.send_share_invite_email")
def test_share_sends_to_correct_email_and_project(mock_send, client, auth_headers):
    project_id = create_project(client, auth_headers, name="Specific Project Name")
    client.get(
        f"/project/{project_id}/share?with=invitee@example.com", headers=auth_headers
    )

    mock_send.assert_called_once()
    call_kwargs = mock_send.call_args.kwargs
    assert call_kwargs["to_email"] == "invitee@example.com"
    assert call_kwargs["project_name"] == "Specific Project Name"
    assert "join_link" in call_kwargs


@patch("app.email.send_share_invite_email")
def test_share_nonexistent_project(mock_send, client, auth_headers):
    response = client.get(
        "/project/999/share?with=invitee@example.com", headers=auth_headers
    )
    assert response.status_code == 404
    mock_send.assert_not_called()


def test_join_with_invalid_token(client, auth_headers):
    response = client.get("/join?token=not-a-real-token", headers=auth_headers)
    assert response.status_code == 400


def test_join_requires_auth(client):
    response = client.get("/join?token=whatever")
    assert response.status_code == 401


@patch("app.email.send_share_invite_email")
def test_join_success(
    mock_send, client, auth_headers, second_user_headers, second_user_payload
):
    project_id = create_project(client, auth_headers)
    share_response = client.get(
        f"/project/{project_id}/share?with={second_user_payload['email']}",
        headers=auth_headers,
    )
    token = share_response.json()["join_link"].split("token=")[1]

    response = client.get(f"/join?token={token}", headers=second_user_headers)
    assert response.status_code == 200
    assert response.json()["role"] == "editor"

    # Confirm they actually gained access
    project_check = client.get(
        f"/project/{project_id}/info", headers=second_user_headers
    )
    assert project_check.status_code == 200


@patch("app.email.send_share_invite_email")
def test_join_rejects_mismatched_email(
    mock_send, client, auth_headers, second_user_headers
):
    project_id = create_project(client, auth_headers)
    # Share link issued for a DIFFERENT email than second_user's own
    share_response = client.get(
        f"/project/{project_id}/share?with=not-second-user@example.com",
        headers=auth_headers,
    )
    token = share_response.json()["join_link"].split("token=")[1]

    response = client.get(f"/join?token={token}", headers=second_user_headers)
    assert response.status_code == 403


@patch("app.email.send_share_invite_email")
def test_join_is_idempotent_for_existing_member(
    mock_send, client, auth_headers, second_user_headers, second_user_payload
):
    project_id = create_project(client, auth_headers)
    share_response = client.get(
        f"/project/{project_id}/share?with={second_user_payload['email']}",
        headers=auth_headers,
    )
    token = share_response.json()["join_link"].split("token=")[1]

    first_join = client.get(f"/join?token={token}", headers=second_user_headers)
    assert first_join.status_code == 200

    # Same token used twice shouldn't error out
    second_join = client.get(f"/join?token={token}", headers=second_user_headers)
    assert second_join.status_code == 200


def test_join_expired_token(
    client, auth_headers, second_user_headers, second_user_payload
):
    # Build an already-expired token directly, bypassing the /share endpoint's 48h default
    from datetime import timedelta

    expired_token = security.create_share_token(
        project_id=1,
        email=second_user_payload["email"],
        expires_delta=timedelta(hours=-1),
    )
    response = client.get(f"/join?token={expired_token}", headers=second_user_headers)
    assert response.status_code == 400
