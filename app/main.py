import io
from typing import List
import uuid

from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import timedelta

from . import crud, models, schemas, security, s3
from .database import get_db
from .config import settings

app = FastAPI(title="Project Management API", version="1.0.0")

ALLOWED_EXTENSIONS = {".pdf", ".docx"}

# ==========================================
# SECURITY DEPENDENCIES
# ==========================================


def require_role(*allowed_roles: models.ProjectRole):
    """
    Returns a FastAPI dependency that confirms the current user is a member
    of the project (via path param `project_id`) with one of the given roles.
    Raises 404 if the project doesn't exist, 403 if the role doesn't match.
    """
    def dependency(
        project_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(security.get_current_user),
    ) -> models.ProjectMember:
        membership = crud.get_membership_or_404(db, project_id, current_user.id)
        if membership.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions to perform this action",
            )
        return membership

    return dependency


def require_document_role(*allowed_roles: models.ProjectRole):
    """
    Like require_role, but resolves the project via the document (path param
    `document_id`) instead of directly from the path. Returns (document, membership).
    """
    def dependency(
        document_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(security.get_current_user),
    ):
        document, membership = crud.get_document_membership_or_404(db, document_id, current_user.id)
        if membership.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions to perform this action",
            )
        return document, membership

    return dependency


require_document_editor_or_owner = require_document_role(
    models.ProjectRole.OWNER, models.ProjectRole.EDITOR)


require_owner = require_role(models.ProjectRole.OWNER)
require_editor_or_owner = require_role(models.ProjectRole.OWNER, models.ProjectRole.EDITOR)

# ==========================================
# AUTHENTICATION ROUTES
# ==========================================


@app.get("/", status_code=status.HTTP_200_OK)
def root():
    return {"message": "API is running successfully"}


@app.post(
    "/auth", status_code=status.HTTP_201_CREATED, response_model=schemas.UserResponse
)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """Create a new user in the database."""
    db_user = crud.get_user_by_username(db, username=user.username)

    # Check if the username is already registered
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )

    # Hash the password before storing it
    hashed_password = security.get_password_hash(user.password)

    return crud.create_user(db=db, user=user, hashed_password=hashed_password)


@app.post("/login", response_model=schemas.Token, status_code=status.HTTP_200_OK)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    """Authenticate the user and return a JWT token if the credentials are valid."""
    user = crud.get_user_by_username(db, username=form_data.username)

    # Verify the provided password against the hashed password stored in the database
    if not user or not security.verify_password(
        form_data.password, user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Generate JWT token for the authenticated user
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


# ==========================================
# PROJECT ROUTES
# ==========================================
@app.post(
    "/projects",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.ProjectResponse,
    tags=["Projects"],
)
def create_project(
    project: schemas.ProjectCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    """Create a new project for the authenticated user."""
    return crud.create_project(db=db, project=project, owner_id=current_user.id)


@app.get(
    "/projects",
    status_code=status.HTTP_200_OK,
    response_model=list[schemas.ProjectResponse],
    tags=["Projects"],
)
def get_projects(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    """Retrieve all projects that the authenticated user is a member of."""
    return crud.get_projects(db=db, user_id=current_user.id)


@app.get(
    "/project/{project_id}/info",
    status_code=status.HTTP_200_OK,
    response_model=schemas.ProjectResponse,
    tags=["Projects"],
)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    """Retrieve information about a specific project."""
    crud.get_membership_or_404(db, project_id, current_user.id)
    return crud.get_project(db, project_id=project_id)


@app.put(
    "/project/{project_id}/info",
    status_code=status.HTTP_200_OK,
    response_model=schemas.ProjectResponse,
    tags=["Projects"],
)
def update_project(
    project_id: int,
    project: schemas.ProjectCreate,
    db: Session = Depends(get_db),
    membership: models.ProjectMember = Depends(require_editor_or_owner),
):
    """Update information about a specific project."""
    return crud.update_project(db=db, project_id=project_id, project=project)


@app.delete("/project/{project_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Projects"])
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    membership: models.ProjectMember = Depends(require_owner),
):
    documents = crud.get_documents_by_project(db, project_id)
    for document in documents:
        s3.delete_file(document.s3_key)

    crud.delete_project(db=db, project_id=project_id)
    return None


# ==========================================
# PROJECT DOCUMENTS (Upload & List)
# ==========================================
@app.get(
    "/project/{project_id}/documents",
    status_code=status.HTTP_200_OK,
    response_model=list[schemas.DocumentResponse],
    tags=["Documents"],
)
def get_project_documents(
    project_id: int,
    db: Session = Depends(get_db),
    membership: models.ProjectMember = Depends(require_editor_or_owner)
):
    """Retrieve all documents associated with a specific project."""
    return crud.get_documents_by_project(db, project_id=project_id)


@app.post(
    "/project/{project_id}/documents",
    status_code=status.HTTP_201_CREATED,
    response_model=list[schemas.DocumentResponse],
    tags=["Documents"],
)
def upload_document(
    project_id: int,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    membership: models.ProjectMember = Depends(require_editor_or_owner)
):
    """Upload one or more documents to a specific project (owner and editor only)."""
    created_documents = []
    for file in files:
        extension = (
            "." + file.filename.rsplit(".", 1)[-1].lower()
            if "." in file.filename
            else ""
        )
        if extension not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=f"File '{file.filename}' has an unsupported type. Only .pdf & .docx allowed",
            )

        contents = file.file.read()
        file_size = len(contents)

        s3_key = f"projects/{project_id}/{uuid.uuid4()}{extension}"
        s3.upload_file(io.BytesIO(contents), s3_key, file.content_type)

        document = schemas.DocumentCreate(
            file_name=file.filename, file_size=file_size, s3_key=s3_key
        )
        created_documents.append(
            crud.create_document(db=db, document=document, project_id=project_id)
        )

    return created_documents


# ==========================================
# INDIVIDUAL DOCUMENTS (Download, Update, Delete)
# ==========================================
@app.get("/document/{document_id}", tags=["Documents"])
def download_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    """Download document, if the user has access to the corresponding project"""
    document, _ = crud.get_document_membership_or_404(db, document_id, current_user.id)
    url = s3.generate_presigned_url(document.s3_key)
    return RedirectResponse(url)


@app.put(
        "/document/{document_id}",
        status_code=status.HTTP_200_OK,
        response_model=schemas.DocumentResponse,
        tags=["Documents"])
def update_document(
    document_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    document_and_membership: tuple = Depends(require_document_editor_or_owner),
):
    """Update an existing document (owner and editor only).
    This will overwrite the existing file in S3 and update the metadata in the database."""
    document, membership = document_and_membership

    extension = "." + file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Only .pdf & .docx are allowed.")

    contents = file.file.read()
    file_size = len(contents)

    s3.upload_file(io.BytesIO(contents), document.s3_key, file.content_type)

    return crud.update_document(db, document_id, file_name=file.filename, file_size=file_size)


@app.delete(
        "/document/{document_id}",
        status_code=status.HTTP_204_NO_CONTENT,
        tags=["Documents"])
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    document_and_membership: tuple = Depends(require_document_editor_or_owner),
):
    """Delete a specific document (owner and editor only)."""
    document, membership = document_and_membership

    s3.delete_file(document.s3_key)
    crud.delete_document(db, document_id)
    return None


# ==========================================
# ACCESS & INVITATIONS
# ==========================================
@app.post(
    "/project/{project_id}/invite",
    status_code=status.HTTP_200_OK,
    response_model=schemas.ProjectMemberResponse,
    tags=["Access"],
)
def invite_user(
    project_id: int,
    user: str,
    role: models.InvitableRole = models.InvitableRole.EDITOR,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    """Invite a user to a project (owner only)."""
    # Confirm the project exists and the requester is a member
    membership = crud.get_membership_or_404(db, project_id, current_user.id)

    # Only the owner can invite
    if membership.role != models.ProjectRole.OWNER:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, detail="Only the project owner can invite users"
        )

    # Find the user being invited
    invited_user = crud.get_user_by_username(db, username=user)
    if invited_user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found")

    new_role = models.ProjectRole(role.value)
    existing_member = crud.get_project_member(db, project_id, invited_user.id)

    if existing_member is not None:
        # Already a member — treat this as a role change instead of rejecting
        if existing_member.role == models.ProjectRole.OWNER:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, detail="Cannot change the owner's role"
            )
        return crud.update_project_member_role(db, existing_member, new_role)

    member = schemas.ProjectMemberCreate(
        user_id=invited_user.id,
        project_id=project_id,
        role=models.ProjectRole(role.value),
    )
    return crud.create_project_member(db, member)


# #TODO: terminar los siguientes endpoints:
# # Optional
# @app.get("/project/{project_id}/share", tags=["Access"])
# def share_project(project_id: int, email: str,
#   db: Session =Depends(get_db), current_user = Depends(get_current_user)):
#     """Send a GET /join link with correct hashed token to specified email."""
#     pass
