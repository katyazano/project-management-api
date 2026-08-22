# Project Management API

A REST API for creating, updating, sharing, and deleting projects and their attached documents. Built with FastAPI, PostgreSQL, and SQLAlchemy, with AWS S3 for file storage and Lambda for async file processing.

## Features

- User registration and JWT-based authentication (1 hour token expiry)
- Create, read, update, and delete projects
- Role-based project access — **owner** (full control), **editor** (can edit, cannot delete) and **viewer** (can view, cannot delete or edit)
- Upload, update, download, and remove project documents (`.docx`, `.pdf`)
- Invite other users to a project
- Shareable project links via email

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
| Dependency management | Poetry

## Project Structure

```
.
├── .github/              # Workflows
├── alembic/              # Database migration versions
├── app/
│   ├── main.py          # Route definitions
│   ├── crud.py           # Database access layer
│   ├── models.py         # SQLAlchemy models
│   ├── schemas.py        # Pydantic request/response schemas
│   ├── security.py       # Password hashing, JWT creation/validation
│   ├── config.py         # Environment-based settings
│   └── database.py       # DB engine/session setup
├── docs/                # Project documentation
├── tests/                # Test suite
├── alembic.ini           # Alembic configuration
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
└── README.md
```

## Prerequisites

- Python 3.12+
- Docker and Docker Compose
- Poetry (`pip install poetry`)

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
   | `AWS_ACCESS_KEY_ID` | AWS IAM User key |
   | `AWS_SECRET_ACCESS_KEY` | AWS IAM Secret |
   | `AWS_REGION` | AWS Region | `us-east-1` |
   | `SES_SENDER_EMAIL` | Verified AWS SES email address |

   > Never commit your real `.env` file. Keep `SECRET_KEY` out of version control and rotate it if it's ever exposed.

4. **Build and start the stack**
   ```bash
   docker compose up --build
   ```

   This starts the API and its PostgreSQL database. On startup, SQLAlchemy creates any tables that don't yet exist.

5. **Verify it's running**

   Visit `http://localhost:8000/` — you should see:
   ```json
   {"message": "API is running successfully"}
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
| `GET` | `/projects` | List all projects the user has access to | Yes |
| `GET` | `/project/{project_id}/info` | Get a project's details | Yes (member) |
| `PUT` | `/project/{project_id}/info` | Update a project's details | Yes (member) |
| `DELETE` | `/project/{project_id}` | Delete a project and its documents | Yes (owner only) |
| `GET` | `/project/{project_id}/documents` | List a project's documents | Yes (member) |
| `POST` | `/project/{project_id}/documents` | Upload document(s) to a project | Yes (member) |
| `GET` | `/document/{document_id}` | Download a document | Yes (member) |
| `PUT` | `/document/{document_id}` | Update a document | Yes (member) |
| `DELETE` | `/document/{document_id}` | Delete a document | Yes (member) |
| `POST` | `/project/{project_id}/invite?user={login}` | Grant another user access to a project | Yes (owner only) |
| `GET` | `/project/{project_id}/share?with={email}` | Email a join link for the project | Yes (owner only) |

## Testing with Postman

A ready-to-use Postman collection is included: [`project-management-api.postman_collection.json`](./project-management-api.postman_collection.json).

1. Open Postman → **Import** → select the file.
2. Requests are grouped into **Auth**, **Projects**, **Documents**, and **Access** folders.
3. Run **Auth → Login** first — it automatically saves the returned JWT into a collection variable, which every other request reuses via Bearer auth.
4. **Projects → Create Project** likewise auto-saves the new `project_id` for use in later requests.
5. For the two file-upload requests (**Upload Document**, **Update Document**), open the **Body** tab and attach a real `.pdf`/`.docx` file before sending — Postman can't pre-fill a file path for security reasons.

Collection variables (`base_url`, `access_token`, `project_id`, `document_id`) can be edited from the collection's **Variables** tab if you need to point at a different host or seed a different starting ID.

## Running Tests

```bash
poetry run pytest
```
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
