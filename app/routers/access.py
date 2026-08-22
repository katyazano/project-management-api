from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app import crud, email, models, schemas, security
from app.config import settings
from app.database import get_db
from app.dependencies import require_owner

router = APIRouter(tags=["Access"])

SHARE_LINK_EXPIRE_HOURS = 48


@router.post(
    "/project/{project_id}/invite",
    status_code=status.HTTP_200_OK,
    response_model=schemas.ProjectMemberResponse,
)
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
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, detail="Cannot change the owner's role"
            )
        return crud.update_project_member_role(db, existing_member, new_role)

    member = schemas.ProjectMemberCreate(
        user_id=invited_user.id, project_id=project_id, role=new_role
    )
    return crud.create_project_member(db, member)


@router.get(
    "/project/{project_id}/share",
    status_code=status.HTTP_200_OK,
    response_model=schemas.ShareLinkResponse,
)
def share_project(
    project_id: int,
    with_: str = Query(alias="with"),
    membership: models.ProjectMember = Depends(require_owner),
    db: Session = Depends(get_db),
):
    project = crud.get_project(db, project_id)

    token = security.create_share_token(
        project_id=project_id,
        email=with_,
        expires_delta=timedelta(hours=SHARE_LINK_EXPIRE_HOURS),
    )
    join_link = f"{settings.APP_BASE_URL}/join?token={token}"

    email.send_share_invite_email(
        to_email=with_, project_name=project.name, join_link=join_link
    )

    return schemas.ShareLinkResponse(
        join_link=join_link, expires_in_hours=SHARE_LINK_EXPIRE_HOURS
    )


@router.get(
    "/join",
    status_code=status.HTTP_200_OK,
    response_model=schemas.ProjectMemberResponse,
)
def join_project(
    token: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    """Join a project via a shareable link."""
    payload = security.decode_share_token(token)
    project_id = payload["project_id"]
    invited_email = payload["email"]

    if current_user.email.lower() != invited_email.lower():
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="This invite link was issued for a different email address",
        )

    project = crud.get_project(db, project_id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Project not found")

    existing_member = crud.get_project_member(db, project_id, current_user.id)
    if existing_member is not None:
        return existing_member

    member = schemas.ProjectMemberCreate(
        user_id=current_user.id,
        project_id=project_id,
        role=models.ProjectRole.EDITOR,
    )
    return crud.create_project_member(db, member)
