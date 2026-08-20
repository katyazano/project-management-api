from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app import crud, models, s3, schemas, security
from app.database import get_db
from app.dependencies import require_editor_or_owner, require_member, require_owner

router = APIRouter(tags=["Projects"])

@router.post("/projects", status_code=status.HTTP_201_CREATED, response_model=schemas.ProjectResponse)
def create_project(
    project: schemas.ProjectCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    """Create a new project for the authenticated user."""
    return crud.create_project(db=db, project=project, owner_id=current_user.id)


@router.get("/projects", status_code=status.HTTP_200_OK, response_model=list[schemas.ProjectResponse])
def get_projects(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    """Retrieve all projects that the authenticated user is a member of."""
    return crud.get_projects(db=db, user_id=current_user.id)

@router.get("/project/{project_id}/info", status_code=status.HTTP_200_OK, response_model=schemas.ProjectResponse)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    membership: models.ProjectMember = Depends(require_member),
):
    """Retrieve information about a specific project."""
    return crud.get_project(db, project_id=project_id)


@router.put("/project/{project_id}/info", status_code=status.HTTP_200_OK, response_model=schemas.ProjectResponse)
def update_project(
    project_id: int,
    project: schemas.ProjectCreate,
    db: Session = Depends(get_db),
    membership: models.ProjectMember = Depends(require_editor_or_owner),
):
    """Update information about a specific project."""
    return crud.update_project(db=db, project_id=project_id, project=project)


@router.delete("/project/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    membership: models.ProjectMember = Depends(require_owner),
):
    """Delete a project and all its associated documents."""
    documents = crud.get_documents_by_project(db, project_id)
    for document in documents:
        s3.delete_file(document.s3_key)
    crud.delete_project(db=db, project_id=project_id)
    return None