def create_project(client, headers, name="Doc Test Project"):
    """Helper function to create a project for testing."""
    response = client.post(
        "/projects",
        json={"name": name, "description": "for doc tests"},
        headers=headers,
    )
    return response.json()["id"]


def test_upload_document_success(mock_s3, client, auth_headers):
    project_id = create_project(client, auth_headers)
    file_content = b"%PDF-1.4 fake pdf content"

    response = client.post(
        f"/project/{project_id}/documents",
        files=[("files", ("test.pdf", file_content, "application/pdf"))],
        headers=auth_headers,
    )

    assert response.status_code == 201
    data = response.json()
    assert len(data) == 1
    assert data[0]["file_name"] == "test.pdf"
    assert data[0]["file_size"] == len(file_content)

    objects = mock_s3.list_objects_v2(Bucket="test-bucket")
    assert "Contents" in objects
    assert len(objects["Contents"]) == 1


def test_upload_document_rejects_bad_extension(mock_s3, client, auth_headers):
    project_id = create_project(client, auth_headers)
    response = client.post(
        f"/project/{project_id}/documents",
        files=[("files", ("test.exe", b"data", "application/octet-stream"))],
        headers=auth_headers,
    )

    assert response.status_code == 400

    objects = mock_s3.list_objects_v2(Bucket="test-bucket")
    assert "Contents" not in objects


def test_upload_document_requires_membership(
    mock_s3, client, auth_headers, second_user_headers
):
    project_id = create_project(client, auth_headers)
    response = client.post(
        f"/project/{project_id}/documents",
        files=[("files", ("test.pdf", b"content", "application/pdf"))],
        headers=second_user_headers,
    )

    assert response.status_code == 403


def test_get_project_documents(mock_s3, client, auth_headers):
    project_id = create_project(client, auth_headers)
    client.post(
        f"/project/{project_id}/documents",
        files=[("files", ("test.pdf", b"content", "application/pdf"))],
        headers=auth_headers,
    )

    response = client.get(f"/project/{project_id}/documents", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_download_document_redirects_to_s3(mock_s3, client, auth_headers):
    project_id = create_project(client, auth_headers)
    upload = client.post(
        f"/project/{project_id}/documents",
        files=[("files", ("test.pdf", b"content", "application/pdf"))],
        headers=auth_headers,
    )
    document_id = upload.json()[0]["id"]

    response = client.get(
        f"/document/{document_id}", headers=auth_headers, follow_redirects=False
    )

    assert response.status_code == 307
    assert "test-bucket.s3.amazonaws.com" in response.headers["location"]
    assert "AWSAccessKeyId" in response.headers["location"]


def test_download_nonexistent_document(client, auth_headers):
    response = client.get("/document/999", headers=auth_headers)
    assert response.status_code == 404


def test_update_document(mock_s3, client, auth_headers):
    project_id = create_project(client, auth_headers)
    upload = client.post(
        f"/project/{project_id}/documents",
        files=[("files", ("test.pdf", b"content", "application/pdf"))],
        headers=auth_headers,
    )
    document_id = upload.json()[0]["id"]

    new_content = b"updated pdf content, longer than the original"
    response = client.put(
        f"/document/{document_id}",
        files={"file": ("updated.pdf", new_content, "application/pdf")},
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["file_name"] == "updated.pdf"
    assert data["file_size"] == len(new_content)


def test_delete_document(mock_s3, client, auth_headers):
    project_id = create_project(client, auth_headers)
    upload = client.post(
        f"/project/{project_id}/documents",
        files=[("files", ("test.pdf", b"content", "application/pdf"))],
        headers=auth_headers,
    )
    document_id = upload.json()[0]["id"]

    assert len(mock_s3.list_objects_v2(Bucket="test-bucket")["Contents"]) == 1

    response = client.delete(f"/document/{document_id}", headers=auth_headers)
    assert response.status_code == 204

    remaining = client.get(f"/project/{project_id}/documents", headers=auth_headers)
    assert remaining.json() == []

    objects_after_delete = mock_s3.list_objects_v2(Bucket="test-bucket")
    assert "Contents" not in objects_after_delete


def test_viewer_cannot_delete_document(
    mock_s3, client, auth_headers, second_user_headers, second_username
):
    project_id = create_project(client, auth_headers)
    upload = client.post(
        f"/project/{project_id}/documents",
        files=[("files", ("test.pdf", b"content", "application/pdf"))],
        headers=auth_headers,
    )
    document_id = upload.json()[0]["id"]

    client.post(
        f"/project/{project_id}/invite?user={second_username}&role=viewer",
        headers=auth_headers,
    )

    response = client.delete(f"/document/{document_id}", headers=second_user_headers)
    assert response.status_code == 403

    assert len(mock_s3.list_objects_v2(Bucket="test-bucket")["Contents"]) == 1


def test_upload_rejected_over_limit(mock_s3, client, auth_headers, monkeypatch):
    monkeypatch.setattr("app.config.settings.MAX_PROJECT_STORAGE_BYTES", 10)
    project_id = create_project(client, auth_headers)

    response = client.post(
        f"/project/{project_id}/documents",
        files=[
            ("files", ("big.pdf", b"more than ten bytes of content", "application/pdf"))
        ],
        headers=auth_headers,
    )

    assert response.status_code == 400

    objects = mock_s3.list_objects_v2(Bucket="test-bucket")
    assert "Contents" not in objects


def test_upload_allowed_within_limit(mock_s3, client, auth_headers, monkeypatch):
    monkeypatch.setattr("app.config.settings.MAX_PROJECT_STORAGE_BYTES", 1024 * 1024)
    project_id = create_project(client, auth_headers)

    response = client.post(
        f"/project/{project_id}/documents",
        files=[("files", ("small.pdf", b"tiny content", "application/pdf"))],
        headers=auth_headers,
    )

    assert response.status_code == 201
    objects = mock_s3.list_objects_v2(Bucket="test-bucket")
    assert len(objects["Contents"]) == 1


def test_upload_rejected_when_existing_documents_push_over_limit(
    mock_s3, client, auth_headers, monkeypatch
):
    """Confirms the limit checks cumulative project usage, not just the new upload's own size."""
    monkeypatch.setattr("app.config.settings.MAX_PROJECT_STORAGE_BYTES", 20)
    project_id = create_project(client, auth_headers)

    first = client.post(
        f"/project/{project_id}/documents",
        files=[
            ("files", ("first.pdf", b"fifteen bytes!!", "application/pdf"))
        ],  # 15 bytes
        headers=auth_headers,
    )
    assert first.status_code == 201

    second = client.post(
        f"/project/{project_id}/documents",
        files=[
            ("files", ("second.pdf", b"ten bytes!", "application/pdf"))
        ],  # 10 bytes, 15+10 > 20
        headers=auth_headers,
    )
    assert second.status_code == 400

    objects = mock_s3.list_objects_v2(Bucket="test-bucket")
    assert len(objects["Contents"]) == 1
