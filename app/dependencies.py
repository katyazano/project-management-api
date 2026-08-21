from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import crud, models, security
from app.database import get_db


def require_member(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
) -> models.ProjectMember:
    project = crud.get_project(db, project_id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Project not found")

    membership = crud.get_membership(db, project_id, current_user.id)
    if membership is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="No access to this project")

    return membership


def require_role(*allowed_roles: models.ProjectRole):
    def dependency(
        project_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(security.get_current_user),
    ) -> models.ProjectMember:
        membership = require_member(project_id, db, current_user)
        if membership.role not in allowed_roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Not enough permissions to perform this action")
        return membership
    return dependency


def require_document_member(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    document = crud.get_document(db, document_id)
    if document is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Document not found")

    membership = crud.get_membership(db, document.project_id, current_user.id)
    if membership is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="No access to this project")

    return document, membership


def require_document_role(*allowed_roles: models.ProjectRole):
    def dependency(
        document_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(security.get_current_user),
    ):
        document, membership = require_document_member(document_id, db, current_user)
        if membership.role not in allowed_roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Not enough permissions to perform this action")
        return document, membership
    return dependency


require_owner = require_role(models.ProjectRole.OWNER)
require_editor_or_owner = require_role(models.ProjectRole.OWNER, models.ProjectRole.EDITOR)
require_document_editor_or_owner = require_document_role(models.ProjectRole.OWNER, models.ProjectRole.EDITOR)