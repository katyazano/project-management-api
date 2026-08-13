from sqlalchemy.orm import Session
from . import models, schemas
from fastapi import HTTPException, status

# ==========================================
# USERS
# ==========================================
def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()

def create_user(db: Session, user: schemas.UserCreate, hashed_password: str):
    db_user = models.User(
        username=user.username, 
        email=user.email, 
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# ==========================================
# PROJECTS
# ==========================================
def get_project(db: Session, project_id: int):
    return db.query(models.Project).filter(models.Project.id == project_id).first()

def get_projects(db: Session, user_id: int):
    # Return projects with user access
    return (
        db.query(models.Project)
        .join(models.Document, isouter=True)
        .join(models.ProjectMember)
        .filter(models.ProjectMember.user_id == user_id)
        .all()
        
    )

def create_project(db: Session, project: schemas.ProjectCreate, owner_id: int):
    db_project = models.Project(**project.model_dump())
    db.add(db_project)
    
    # flush to get project id before commit
    db.flush()
    
    # the owner is automatically added as a member of the project with the role of OWNER
    db_member = models.ProjectMember(
        user_id=owner_id,
        project_id=db_project.id,
        role=models.ProjectRole.OWNER
    )
    db.add(db_member)

    # Commit the transaction to save both the project and the member
    db.commit()
    db.refresh(db_project)
    return db_project

def update_project(db: Session, project_id: int, project: schemas.ProjectCreate):
    db_project = get_project(db, project_id)
    for key, value in project.model_dump().items():
        setattr(db_project, key, value)
    db.commit()
    db.refresh(db_project)
    return db_project

def delete_project(db: Session, project_id: int):
    db_project = get_project(db, project_id)
    if db_project:
        db.delete(db_project)
        db.commit()
    return db_project

# ==========================================
# PROJECT MEMBERS
# ==========================================
def create_project_member(db: Session, member: schemas.ProjectMemberCreate):
    db_member = models.ProjectMember(**member.model_dump())
    db.add(db_member)
    db.commit()
    db.refresh(db_member)
    return db_member

def get_project_member(db: Session, project_id: int, user_id: int):
    return (
        db.query(models.ProjectMember)
        .filter(
            models.ProjectMember.project_id == project_id,
            models.ProjectMember.user_id == user_id,
        )
        .first()
    )

def update_project_member_role(db: Session, member: models.ProjectMember, role: models.ProjectRole):
    member.role = role
    db.commit()
    db.refresh(member)
    return member

def is_owner(db: Session, project_id: int, user_id: int) -> bool:
    member = (
        db.query(models.ProjectMember)
        .filter(
            models.ProjectMember.project_id == project_id,
            models.ProjectMember.user_id == user_id,
        )
        .first()
    )
    return member is not None and member.role == models.ProjectRole.OWNER


# ==========================================
# DOCUMENTS
# ==========================================
def create_document(db: Session, document: schemas.DocumentCreate, project_id: int):
    db_document = models.Document(**document.model_dump(), project_id=project_id)
    db.add(db_document)
    db.commit()
    db.refresh(db_document)
    return db_document

def get_documents_by_project(db: Session, project_id: int):
    return db.query(models.Document).filter(models.Document.project_id == project_id).all()

def get_document(db: Session, document_id: int):
    return db.query(models.Document).filter(models.Document.id == document_id).first()

def get_document_membership_or_404(db: Session, document_id: int, user_id: int):
    """Confirms the document exists and the user has access to its parent project."""
    document = get_document(db, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    membership = get_membership_or_404(db, document.project_id, user_id)
    return document, membership

def update_document(db: Session, document_id: int, file_name: str, file_size: int):
    db_document = get_document(db, document_id)
    db_document.file_name = file_name
    db_document.file_size = file_size
    db.commit()
    db.refresh(db_document)
    return db_document

def delete_document(db: Session, document_id: int):
    db_document = get_document(db, document_id)
    if db_document:
        db.delete(db_document)
        db.commit()
    return db_document


# ==========================================
# HELPERS
# ==========================================
def get_membership_or_404(db: Session, project_id: int, user_id: int) -> models.ProjectMember:
    """
    Confirms the project exists and the user is a member of it.
    Raises 404 if the project doesn't exist, 403 if the user has no access.
    Returns the ProjectMember row (so callers can check .role).
    """
    project = get_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    member = (
        db.query(models.ProjectMember)
        .filter(
            models.ProjectMember.project_id == project_id,
            models.ProjectMember.user_id == user_id,
        )
        .first()
    )
    if member is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to this project")

    return member