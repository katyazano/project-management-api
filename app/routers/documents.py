import io
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app import crud, models, s3, schemas
from app.config import settings
from app.database import get_db
from app.dependencies import (
    require_document_editor_or_owner,
    require_document_member,
    require_editor_or_owner,
    require_member,
)

router = APIRouter(tags=["Documents"])

ALLOWED_EXTENSIONS = {".pdf", ".docx"}


@router.get(
    "/project/{project_id}/documents",
    status_code=status.HTTP_200_OK,
    response_model=list[schemas.DocumentResponse],
)
def get_project_documents(
    project_id: int,
    db: Session = Depends(get_db),
    membership: models.ProjectMember = Depends(require_member),
):
    """Retrieve all documents associated with a specific project."""
    return crud.get_documents_by_project(db, project_id=project_id)


@router.post(
    "/project/{project_id}/documents",
    status_code=status.HTTP_201_CREATED,
    response_model=list[schemas.DocumentResponse],
)
def upload_document(
    project_id: int,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    membership: models.ProjectMember = Depends(require_editor_or_owner),
):
    """Upload one or more documents to a specific project (owner and editor only)."""
    file_data = []
    for file in files:
        extension = (
            "." + file.filename.rsplit(".", 1)[-1].lower()
            if "." in file.filename
            else ""
        )
        if extension not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"File '{file.filename}' has an unsupported type. "
                "Only .pdf and .docx are allowed.",
            )
        contents = file.file.read()
        file_data.append((file, contents, extension))

    incoming_size = sum(len(contents) for _, contents, _ in file_data)
    current_usage = crud.get_project_storage_used(db, project_id)

    if current_usage + incoming_size > settings.MAX_PROJECT_STORAGE_BYTES:
        remaining = max(settings.MAX_PROJECT_STORAGE_BYTES - current_usage, 0)
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=(
                f"This upload would exceed the project's storage limit. "
                f"Remaining space: {remaining} bytes, requested: {incoming_size} bytes."
            ),
        )

    created_documents = []
    for file, contents, extension in file_data:
        s3_key = f"projects/{project_id}/{uuid.uuid4()}{extension}"
        s3.upload_file(io.BytesIO(contents), s3_key, file.content_type)
        document = schemas.DocumentCreate(
            file_name=file.filename, file_size=len(contents), s3_key=s3_key
        )
        created_documents.append(
            crud.create_document(db=db, document=document, project_id=project_id)
        )
    return created_documents


@router.get("/document/{document_id}")
def download_document(
    document_id: int,
    document_and_membership: tuple = Depends(require_document_member),
):
    """Download a document if the user is a member of the parent project."""
    document, _ = document_and_membership
    url = s3.generate_presigned_url(document.s3_key)
    return RedirectResponse(url)


@router.put(
    "/document/{document_id}",
    status_code=status.HTTP_200_OK,
    response_model=schemas.DocumentResponse,
)
def update_document(
    document_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    document_and_membership: tuple = Depends(require_document_editor_or_owner),
):
    """Update a document's file if the user is an editor or owner of the parent project."""
    document, membership = document_and_membership
    extension = (
        "." + file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    )
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="Only .pdf and .docx are allowed."
        )

    contents = file.file.read()
    new_size = len(contents)

    current_usage = (
        crud.get_project_storage_used(db, document.project_id) - document.file_size
    )
    if current_usage + new_size > settings.MAX_PROJECT_STORAGE_BYTES:
        remaining = max(settings.MAX_PROJECT_STORAGE_BYTES - current_usage, 0)
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=(
                f"This update would exceed the project's storage limit. "
                f"Remaining space: {remaining} bytes, requested: {new_size} bytes."
            ),
        )

    s3.upload_file(io.BytesIO(contents), document.s3_key, file.content_type)
    return crud.update_document(
        db, document_id, file_name=file.filename, file_size=new_size
    )


@router.delete("/document/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    document_and_membership: tuple = Depends(require_document_editor_or_owner),
):
    """Delete a document if the user is an editor or owner of the parent project."""
    document, membership = document_and_membership
    s3.delete_file(document.s3_key)
    crud.delete_document(db, document_id)
    return None
