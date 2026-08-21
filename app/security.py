from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.config import settings
from app.database import get_db

# Bcrypt configuration for password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 configuration for token-based authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


# ==========================================
# PASSWORD (CryptContext)
# ==========================================


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generates a hash for a given password using bcrypt."""
    return pwd_context.hash(password)


# ==========================================
# TOKENS (JWT)
# ==========================================


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Creates and signs a JSON Web Token (JWT)."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=60)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def create_share_token(
        project_id: int,
        email: str,
        expires_delta: timedelta = timedelta(hours=48)) -> str:
    """Creates a signed, time-limited token for sharing project access via email."""
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode = {
        "project_id": project_id,
        "email": email,
        "purpose": "project_share",
        "exp": expire,
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

# ==========================================
# DECODE TOKEN AND GET CURRENT USER
# ==========================================


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> models.User:
    """
    Decodes the JWT, validates it, and retrieves current user from db.
    This function is injected into protected routes via Depends().
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Decode token
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )

        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception

        # Pydantic validation
        token_data = schemas.TokenData(username=username)

    except InvalidTokenError:
        raise credentials_exception

    # Search for the user in the database
    user = crud.get_user_by_username(db, username=token_data.username)
    if user is None:
        raise credentials_exception

    return user


def decode_share_token(token: str) -> dict:
    """Decodes and validates a share token. Raises HTTPException on any failure."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid or expired share link",
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except InvalidTokenError:
        raise credentials_exception

    if payload.get("purpose") != "project_share":
        raise credentials_exception

    return payload