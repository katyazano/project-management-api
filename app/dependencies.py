from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import crud, models, security
from app.database import get_db


def require_member(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
) -> models.ProjectMember:
    """Any project member (owner, editor, or viewer) may proceed."""
    return crud.get_membership_or_404(db, project_id, current_user.id)


def require_role(*allowed_roles: models.ProjectRole):
    """Factory: returns a dependency that only lets the given roles through."""
    def dependency(
        project_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(security.get_current_user),
    ) -> models.ProjectMember:
        membership = crud.get_membership_or_404(db, project_id, current_user.id)
        if membership.role not in allowed_roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN,
                                detail="Not enough permissions to perform this action")
        return membership
    return dependency


def require_document_member(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    """Same as require_member, but resolved through a document_id instead of project_id."""
    return crud.get_document_membership_or_404(db, document_id, current_user.id)


def require_document_role(*allowed_roles: models.ProjectRole):
    """Document-keyed equivalent of require_role."""
    def dependency(
        document_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(security.get_current_user),
    ):
        document, membership = crud.get_document_membership_or_404(db, document_id, current_user.id)
        if membership.role not in allowed_roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN,
                                detail="Not enough permissions to perform this action")
        return document, membership
    return dependency


require_owner = require_role(models.ProjectRole.OWNER)
require_editor_or_owner = require_role(models.ProjectRole.OWNER, models.ProjectRole.EDITOR)
require_document_editor_or_owner = require_document_role(models.ProjectRole.OWNER, models.ProjectRole.EDITOR)