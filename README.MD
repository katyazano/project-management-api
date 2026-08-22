# Project Management API

A REST API for creating, updating, sharing, and deleting projects and their attached documents. Built with FastAPI, PostgreSQL, and SQLAlchemy, with AWS S3 for file storage and AWS SES for email delivery.

## Features

- User registration and JWT-based authentication (1 hour token expiry)
- Create, read, update, and delete projects
- Role-based project access — **owner** (full control), **editor** (can edit, cannot delete) and **viewer** (can view, cannot delete or edit)
- Upload, update, download, and remove project documents (`.docx`, `.pdf`)
- Per-project storage limit, enforced across all uploaded documents
- Invite other users to a project, or change an existing member's role
- Shareable project links via email (AWS SES), redeemable via a `/join` link

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.12+ |
| Web framework | FastAPI & Pydantic |
| Database | PostgreSQL |
| ORM & Migrations | SQLAlchemy + Alembic |
| Auth | JWT (PyJWT) + bcrypt |
| Cloud Services | AWS S3 (Storage) + AWS SES (Emails) |
| Testing | Pytest + Moto (AWS Mocking) |
| Containerization | Docker / Docker Compose (Multi-stage builds) |
| CI/CD | GitHub Actions |
| Dependency management | Poetry |

## Project Structure

```
.
├── .github/               # Workflows
├── alembic/                # Database migration versions
├── app/
│   ├── main.py             # App instance, router registration
│   ├── routers/             # Route definitions, grouped by resource
│   │   ├── auth.py           # /auth, /login
│   │   ├── projects.py       # /projects, /project/{id}/info
│   │   ├── documents.py      # /project/{id}/documents, /document/{id}
│   │   └── access.py         # /project/{id}/invite, /project/{id}/share, /join
│   ├── dependencies.py      # Reusable auth/role-checking dependencies
│   ├── crud.py              # Database access layer (no HTTP concerns)
│   ├── models.py            # SQLAlchemy models
│   ├── schemas.py           # Pydantic request/response schemas
│   ├── security.py          # Password hashing, JWT creation/validation
│   ├── s3.py                # S3 upload/download/delete helpers
│   ├── email.py             # SES email sending
│   ├── config.py            # Environment-based settings
│   └── database.py          # DB engine/session setup
├── docs/                  # Project documentation (includes schema.sql)
├── tests/                 # Test suite
├── alembic.ini             # Alembic configuration
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
└── README.md
```

## Prerequisites

- Python 3.12+
- Docker and Docker Compose
- Poetry (`pip install poetry`)
- An AWS account with an S3 bucket and a verified SES sender identity

## Setup & Installation

1. **Clone the repository**
   ```bash
   git clone <repo-url>
   cd <repo-directory>
   ```

2. **Create your environment file**

   Copy the example file and fill in your own values:
   ```bash
   cp .env.example .env
   ```

3. **Environment variables**

   | Variable | Description | Default |
   |---|---|---|
   | `POSTGRES_USER` | Database username | — |
   | `POSTGRES_PASSWORD` | Database password | — |
   | `POSTGRES_DB` | Database name | — |
   | `POSTGRES_HOST` | Database host | — |
   | `POSTGRES_PORT` | Database port | `5432` |
   | `SECRET_KEY` | Secret used to sign JWTs | — |
   | `ALGORITHM` | JWT signing algorithm | `HS256` |
   | `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT lifetime in minutes | `60` |
   | `AWS_ACCESS_KEY_ID` | AWS IAM user key | — |
   | `AWS_SECRET_ACCESS_KEY` | AWS IAM user secret | — |
   | `AWS_REGION` | AWS region | `us-east-1` |
   | `S3_BUCKET_NAME` | S3 bucket used for document storage | — |
   | `SES_SENDER_EMAIL` | Verified AWS SES sender address | — |
   | `APP_BASE_URL` | Base URL used to build `/join` links in share emails | `http://localhost:8000` |
   | `MAX_PROJECT_STORAGE_BYTES` | Max combined document size allowed per project, in bytes | `52428800` (50 MB) |

   > Never commit your real `.env` file. Keep `SECRET_KEY` out of version control and rotate it if it's ever exposed.

4. **Build and start the stack**
   ```bash
   docker compose up --build
   ```

   This starts the API and its PostgreSQL database. The API container automatically runs `alembic upgrade head` on startup, applying any pending migrations before the server boots — no manual schema step needed.

5. **Verify it's running**

   Visit `http://localhost:8000/` — you should see:
   ```json
   {"message": "API is running successfully"}
   ```

### Running locally without Docker

If you're running the app directly (e.g. `poetry run uvicorn app.main:app --reload`) against a Postgres instance, apply migrations manually first:
```bash
poetry run alembic upgrade head
```
Whenever the models change, generate and apply a new migration:
```bash
poetry run alembic revision --autogenerate -m "describe the change"
poetry run alembic upgrade head
```

## API Documentation

Interactive Swagger docs are available once the server is running:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Authentication

1. Register a user with `POST /auth`.
2. Log in with `POST /login` (form-encoded `username` and `password`) to receive a JWT.
3. Include the token on all subsequent requests:
   ```
   Authorization: Bearer <access_token>
   ```
4. In Swagger UI, click **Authorize** and enter your credentials — the token is attached to requests automatically.

## API Endpoints

| Method | Endpoint | Description | Auth required |
|---|---|---|---|
| `POST` | `/auth` | Register a new user | No |
| `POST` | `/login` | Log in, receive a JWT | No |
| `POST` | `/projects` | Create a project (creator becomes owner) | Yes |
| `GET` | `/projects` | List all projects the user has access to, with documents | Yes |
| `GET` | `/project/{project_id}/info` | Get a project's details | Yes (any member) |
| `PUT` | `/project/{project_id}/info` | Update a project's details (both fields required) | Yes (owner or editor) |
| `DELETE` | `/project/{project_id}` | Delete a project, its documents, and their S3 files | Yes (owner only) |
| `GET` | `/project/{project_id}/documents` | List a project's documents | Yes (any member) |
| `POST` | `/project/{project_id}/documents` | Upload document(s) to a project, subject to the storage limit | Yes (owner or editor) |
| `GET` | `/document/{document_id}` | Download a document (redirects to a presigned S3 URL) | Yes (any member) |
| `PUT` | `/document/{document_id}` | Update a document | Yes (owner or editor) |
| `DELETE` | `/document/{document_id}` | Delete a document and its S3 file | Yes (owner or editor) |
| `POST` | `/project/{project_id}/invite?user={login}&role={role}` | Grant a user access, or change an existing member's role | Yes (owner only) |
| `GET` | `/project/{project_id}/share?with={email}` | Email a `/join` link for the project | Yes (owner only) |
| `GET` | `/join?token={token}` | Redeem a share link and join the project | Yes (matching email) |

## Testing with Postman

A ready-to-use Postman collection is included: [`project-management-api.postman_collection.json`](./project-management-api.postman_collection.json).

1. Open Postman → **Import** → select the file.
2. Requests are grouped into **Auth**, **Projects**, **Documents**, and **Access** folders.
3. Run **Auth → Login** first — it automatically saves the returned JWT into a collection variable, which every other request reuses via Bearer auth.
4. **Projects → Create Project** likewise auto-saves the new `project_id` for use in later requests.
5. For the two file-upload requests (**Upload Document**, **Update Document**), open the **Body** tab and attach a real `.pdf`/`.docx` file before sending — Postman can't pre-fill a file path for security reasons.
6. **Access → Share Project** auto-extracts the token from the returned join link into a `share_token` variable, ready for **Access → Join Project**. Note that redeeming the link requires being logged in as the invited user (matching `invite_email`) — re-run **Auth → Login** with that user's credentials before calling Join.

Collection variables (`base_url`, `access_token`, `project_id`, `document_id`, `invite_email`, `share_token`) can be edited from the collection's **Variables** tab if you need to point at a different host or seed different starting values.

## Running Tests

```bash
poetry run pytest
```

Tests run against an in-memory SQLite database and mock AWS S3 (via `moto`) and SES, so no real AWS credentials or Postgres instance are needed to run the suite.

## Key Scaling Upgrades

- Load Balancing: An ALB to distribute traffic across multiple container replicas.
- Microservices: Decoupling Auth, Projects, and Documents into isolated services to allow independent scaling.
- Database Sharding & Caching: Dedicated databases per service and a Redis cache to optimize repetitive read queries.
- Asynchronous Processing: Moving AWS SES email dispatching to a background worker listening to an SQS queue, ensuring the API responds instantly to users without waiting for cloud providers.

## Database Design & ORM

While the application relies on **SQLAlchemy** as its ORM and **Alembic** for automated migrations, the foundational database architecture is strictly normalized to the Third Normal Form (3NF).

To demonstrate the underlying relational logic, integrity constraints, and performance indexing without the ORM abstraction, a standalone raw SQL definition is provided:
- **[`schema.sql`](./docs/schema.sql):** Contains the pure PostgreSQL DDL statements for custom ENUMs, tables, and indexes.

## Roadmap

See [`CHALLENGE.md`](./CHALLENGE.md) for the full original project brief and requirements.
