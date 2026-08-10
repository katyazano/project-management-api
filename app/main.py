from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta

from . import crud, models, schemas, security
from .database import engine, get_db
from .config import settings

# SQLAlchemy creates the database tables based on the models defined in models.py
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Project Management API", version="1.0.0")

# ==========================================
# AUTHENTICATION ROUTES 
# ==========================================
@app.get("/", status_code=status.HTTP_200_OK)
def root():
    return {"message": "API is running successfully"}

@app.post("/auth", status_code=status.HTTP_201_CREATED, response_model=schemas.UserResponse)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """Create a new user in the database after checking if the username is already registered and hashing the password."""
    db_user = crud.get_user_by_username(db, username=user.username)

    # Check if the username is already registered
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Username already registered"
        )
    
    # Hash the password before storing it
    hashed_password = security.get_password_hash(user.password)

    return crud.create_user(db=db, user=user, hashed_password=hashed_password)

@app.post("/login", response_model=schemas.Token, status_code=status.HTTP_200_OK)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Authenticate the user and return a JWT token if the credentials are valid."""
    user = crud.get_user_by_username(db, username=form_data.username)

    # Verify the provided password against the hashed password stored in the database
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Generate JWT token for the authenticated user
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.username}, 
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# ==========================================
# PROJECT ROUTES 
# ==========================================
@app.post("/projects", status_code=status.HTTP_201_CREATED, response_model=schemas.ProjectResponse, tags=["Projects"])
def create_project(
    project: schemas.ProjectCreate, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    """Create a new project for the authenticated user."""
    return crud.create_project(db=db, project=project, owner_id=current_user.id)

@app.get("/projects", status_code=status.HTTP_200_OK, response_model=list[schemas.ProjectResponse], tags=["Projects"])
def get_projects(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    """Retrieve all projects that the authenticated user is a member of."""
    return crud.get_projects(db=db, user_id=current_user.id)

@app.get("/project/{project_id}/info", status_code=status.HTTP_200_OK, response_model=schemas.ProjectResponse, tags=["Projects"])
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    """Retrieve information about a specific project."""
    membership = crud.get_membership_or_404(db, project_id, current_user.id)
    return crud.get_project(db, project_id=project_id)

@app.put("/project/{project_id}/info", status_code=status.HTTP_200_OK, response_model=schemas.ProjectResponse, tags=["Projects"])
def update_project(
    project_id: int,
    project: schemas.ProjectCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    membership = crud.get_membership_or_404(db, project_id, current_user.id)

    if membership.role == models.ProjectRole.VIEWER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Viewers cannot edit this project")

    return crud.update_project(db=db, project_id=project_id, project=project)

@app.delete("/project/{project_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Projects"])
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    """Delete a specific project (owner only)."""
    db_project = crud.get_project(db, project_id=project_id)
    if db_project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    if not crud.is_owner(db, project_id, current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions to delete this project")

    crud.delete_project(db=db, project_id=project_id)
    return None


# #TODO: terminar los siguientes endpoints:
# # ==========================================
# # PROJECT DOCUMENTS (Upload & List)
# # ==========================================
# @app.get("/project/{project_id}/documents", tags=["Documents"])
# def get_project_documents(project_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
#     """Return all of the project's documents."""
#     pass

# @app.post("/project/{project_id}/documents", tags=["Documents"])
# def upload_document(project_id: int, document: schemas.DocumentCreate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
#     """Upload document/documents for a specific project."""
#     pass

# # ==========================================
# # INDIVIDUAL DOCUMENTS (Download, Update, Delete)
# # ==========================================
# @app.get("/document/{document_id}", tags=["Documents"])
# def download_document(document_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
#     """Download document, if the user has access to the corresponding project."""
#     pass

# @app.put("/document/{document_id}", tags=["Documents"])
# def update_document(document_id: int, document_update: schemas.DocumentUpdate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
#     """Update document."""
#     pass

# @app.delete("/document/{document_id}", tags=["Documents"])
# def delete_document(document_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
#     """Delete document and remove it from the corresponding project."""
#     pass

# # ==========================================
# # ACCESS & INVITATIONS
# # ==========================================
# @app.post("/project/{project_id}/invite", tags=["Access"])
# def invite_user(project_id: int, user: str, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
#     """Grant access to the project for a specific user (owner only)."""
#     # En FastAPI, poner 'user: str' como parámetro lo convierte automáticamente en un Query Parameter (?user=login)
#     pass

# # Optional
# @app.get("/project/{project_id}/share", tags=["Access"])
# def share_project(project_id: int, email: str, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
#     """Send a GET /join link with correct hashed token to specified email."""
#     # Igual aquí, 'email: str' se convierte en el query parameter '?with=email' (podemos renombrar la variable a 'with_email' y mapearla)
#     pass
