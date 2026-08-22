-- ============================================
-- Schema for Project Management Api
-- ============================================

-- ============================================
-- ENUM Types
-- ============================================

CREATE TYPE project_role AS ENUM ('OWNER', 'EDITOR', 'VIEWER');

-- Note: InvitableRole (EDITOR, VIEWER) is used only at the application
-- level for validation and is not mapped to a database table/column.

-- ============================================
-- Table: users
-- ============================================

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR NOT NULL,
    hashed_password VARCHAR NOT NULL,
    email VARCHAR NOT NULL,

    CONSTRAINT uq_users_username UNIQUE (username),
    CONSTRAINT uq_users_email UNIQUE (email)
);

CREATE INDEX ix_users_username ON users (username);
CREATE INDEX ix_users_email ON users (email);

-- ============================================
-- Table: projects
-- ============================================

CREATE TABLE projects (
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL,
    description VARCHAR
);

CREATE INDEX ix_projects_name ON projects (name);

-- ============================================
-- Table: project_members
-- ============================================

CREATE TABLE project_members (
    user_id INTEGER NOT NULL,
    project_id INTEGER NOT NULL,
    role project_role NOT NULL DEFAULT 'VIEWER',

    PRIMARY KEY (user_id, project_id),

    CONSTRAINT fk_project_members_user
        FOREIGN KEY (user_id)
        REFERENCES users (id)
        ON DELETE CASCADE,

    CONSTRAINT fk_project_members_project
        FOREIGN KEY (project_id)
        REFERENCES projects (id)
        ON DELETE CASCADE
);

-- ============================================
-- Table: documents
-- ============================================

CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    file_name VARCHAR NOT NULL,
    s3_key VARCHAR NOT NULL,
    file_size INTEGER NOT NULL,
    project_id INTEGER NOT NULL,

    CONSTRAINT fk_documents_project
        FOREIGN KEY (project_id)
        REFERENCES projects (id)
        ON DELETE CASCADE
);

CREATE INDEX ix_documents_id ON documents (id);