# ---- Stage 1: Build dependencies ----
FROM python:3.12-slim AS builder

# Poetry needs these for building some packages (e.g. psycopg2, bcrypt)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir poetry==1.8.3

# Don't create a virtualenv inside the container — we want deps installed
# directly, since the container itself is already the isolated environment
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false

WORKDIR /app

# Copy only dependency files first, so Docker can cache this layer and skip
# reinstalling dependencies on every rebuild if only your app code changed
COPY pyproject.toml poetry.lock ./
RUN poetry install --no-root --only main

# ---- Stage 2: Runtime image ----
FROM python:3.12-slim

# libpq5 (not -dev) is the runtime lib psycopg2 needs — no compiler needed here
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Pull the installed packages from the builder stage instead of reinstalling
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy your app code and alembic.ini into the container
COPY ./app ./app
COPY ./alembic.ini ./alembic.ini
COPY ./alembic ./alembic

# Run as a non-root user — good practice, some CI/security scanners flag
# containers that run as root by default
RUN useradd --create-home appuser
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]