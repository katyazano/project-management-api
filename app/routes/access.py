from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.database import get_db
from app.dependencies import require_owner

router = APIRouter(tags=["Access"])


@router.post("/project/{project_id}/invite", status_code=status.HTTP_200_OK, response_model=schemas.ProjectMemberResponse)
def invite_user(
    project_id: int,
    user: str,
    role: models.InvitableRole = models.InvitableRole.EDITOR,
    db: Session = Depends(get_db),
    membership: models.ProjectMember = Depends(require_owner),
):
    """Invite a user to a project (owner only)."""
    invited_user = crud.get_user_by_username(db, username=user)
    if invited_user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found")

    new_role = models.ProjectRole(role.value)
    existing_member = crud.get_project_member(db, project_id, invited_user.id)

    if existing_member is not None:
        if existing_member.role == models.ProjectRole.OWNER:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Cannot change the owner's role")
        return crud.update_project_member_role(db, existing_member, new_role)

    member = schemas.ProjectMemberCreate(user_id=invited_user.id, project_id=project_id, role=new_role)
    return crud.create_project_member(db, member)

# #TODO: terminar los siguientes endpoints:
# # Optional
# @app.get("/project/{project_id}/share", tags=["Access"])
# def share_project(project_id: int, email: str,
#   db: Session =Depends(get_db), current_user = Depends(get_current_user)):
#     """Send a GET /join link with correct hashed token to specified email."""
#     pass
