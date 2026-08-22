# Challenge Description

## Theme

Project management / profiles dashboard — a service to create, update, share, and delete project information (details, attached documents).

## Stack

- Python 3.12+
- FastAPI
- PostgreSQL + optional ORM (SQLAlchemy, etc.)
- Docker
- AWS S3 (file storage)
- AWS Lambda functions (image processing, size calculations on S3 events)
- CI/CD: GitHub Actions / GitLab CI (testing / linting / building / pushing to registry / deploy to cloud on merge request)

## Desired Functionality

- User login / auth
- Create / delete projects
- Add / update project info / details — name, description
- Add / update / remove project documents (`.docx`, `.pdf`)
- Share project with other users to access

## API

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/auth` | Create user (login, password, repeat password) |
| `POST` | `/login` | Log in to the service (login, password) |
| `POST` | `/projects` | Create project from details (name, description). Automatically gives access to the created project to the user, making them the owner (admin of the project). |
| `GET` | `/projects` | Get all projects accessible to a user. Returns a list of projects with full info (details + documents). |
| `GET` | `/project/<project_id>/info` | Return a project's details, if the user has access. |
| `PUT` | `/project/<project_id>/info` | Update a project's details — name, description. Returns the updated project's info. |
| `DELETE` | `/project/<project_id>` | Delete a project — can only be performed by the project's owner. Deletes the corresponding documents. |
| `GET` | `/project/<project_id>/documents` | Return all of a project's documents. |
| `POST` | `/project/<project_id>/documents` | Upload document(s) for a specific project. |
| `GET` | `/document/<document_id>` | Download a document, if the user has access to the corresponding project. |
| `PUT` | `/document/<document_id>` | Update a document. |
| `DELETE` | `/document/<document_id>` | Delete a document and remove it from the corresponding project. |
| `POST` | `/project/<project_id>/invite?user=<login>` | Grant access to the project for a specific user. If the request doesn't come from the project owner, results in an error. Granting access gives the receiving user participant permissions. |

### Optional

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/project/<project_id>/share?with=<email>` | Send a `GET /join` link with a correctly hashed token for the requested project to the specified email, which can be opened by a different user in a browser. |

## Phase 2 Additional Tasks

- Normalization + denormalization of DB tables
- Creation of DB with and without an ORM
- S3 + Lambda: image resize (optional), calculation of the sum of a project's file sizes, and applying a limit
- Tests, CI/CD bindings
- Package creation, CI/CD bindings, implementation of related tools (`pyproject.toml`, `tox` || `poetry`)
- Validate all data with Pydantic
- All business-logic requests must be authorized via JWT (including resolving access permissions), issued by `POST /login`. JWT should last 1 hour.

## Implementation Notes

1. All returned data must be in JSON format (except for file data), with proper HTTP status codes.
2. There are two types of access: **owner** (creator of the project, can do anything) and **participant** (user invited to the project, can modify, cannot delete).
3. Exact API parameters/endpoints can be changed/updated upon agreement with the mentor, as long as they cover the described logic.
