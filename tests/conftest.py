import os

os.environ.setdefault("POSTGRES_USER", "test")
os.environ.setdefault("POSTGRES_PASSWORD", "test")
os.environ.setdefault("POSTGRES_DB", "test")
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("ALGORITHM", "HS256")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
os.environ.setdefault("AWS_REGION", "us-east-1")
os.environ.setdefault("S3_BUCKET_NAME", "test-bucket")
os.environ.setdefault("AWS_SECURITY_TOKEN", "testing")
os.environ.setdefault("AWS_SESSION_TOKEN", "testing")

import pytest
import boto3
from moto import mock_aws
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.main import app
from app.database import Base, get_db

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ==========================================
# DATABASE & CLIENT FIXTURES
# ==========================================

@pytest.fixture(scope="function")
def db_session():
    """Fresh tables for every single test, torn down afterward."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """TestClient wired to the in-memory DB instead of real Postgres."""
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

# ==========================================
# AWS MOCK FIXTURE
# ==========================================

@pytest.fixture(scope="function")
def mock_s3():
    """
    Sets up a fake AWS environment using Moto before each test.
    Intercepts boto3 calls so nothing goes to the real AWS.
    """
    with mock_aws():
        s3_client = boto3.client("s3", region_name=os.environ["AWS_REGION"])
        s3_client.create_bucket(Bucket=os.environ["S3_BUCKET_NAME"])
        
        yield s3_client

# ==========================================
# AUTHENTICATION FIXTURES
# ==========================================

@pytest.fixture
def user_payload():
    return {
        "username": "testuser",
        "email": "testuser@example.com",
        "password": "SecurePass1!",
        "repeat_password": "SecurePass1!",
    }


@pytest.fixture
def auth_headers(client, user_payload):
    """Registers a user, logs in, and returns ready-to-use auth headers."""
    client.post("/auth", json=user_payload)
    response = client.post(
        "/login",
        data={"username": user_payload["username"], "password": user_payload["password"]},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def second_user_payload():
    return {
        "username": "seconduser",
        "email": "seconduser@example.com",
        "password": "SecurePass1!",
        "repeat_password": "SecurePass1!",
    }


@pytest.fixture
def second_username(client, second_user_payload):
    """Registers a second user and returns their username."""
    client.post("/auth", json=second_user_payload)
    return second_user_payload["username"]


@pytest.fixture
def second_user_headers(client, second_user_payload):
    """Registers a second user, logs in, and returns ready-to-use auth headers."""
    client.post("/auth", json=second_user_payload)
    response = client.post(
        "/login",
        data={"username": second_user_payload["username"], "password": second_user_payload["password"]},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}