# Nebula - AI-Powered Customer Communication Platform (Backend Foundation)

This is the production-ready backend foundation for Nebula, built with Python 3.13, FastAPI, PostgreSQL (via SQLAlchemy + Alembic), Redis, and Docker.

It provides a modular, fully typed, and structured layout following SOLID principles.

## Features Included
- **Python 3.13 & FastAPI:** Async endpoints, automatic swagger docs, strict typing, and Dependency Injection.
- **PostgreSQL Database:** Integrated via SQLAlchemy async engine (`asyncpg`) and migrations configured via Alembic (async env).
- **Redis Caching & Lock Manager:** Configured for cache invalidation and distributed locking.
- **JWT Authentication:** Scaffolded registration, login, password hashing, and endpoint authorization middleware.
- **Structured JSON Logging:** Structured standard/JSON logger via `structlog` for easy production debugging.
- **Docker Setup:** Production-optimized multi-stage Docker build and a multi-container Docker Compose setup.
- **Health Endpoints:** Comprehensive system health check `/health` returning status of PostgreSQL, Redis, and overall app.
- **Modular Folder Layout:** Separated into `api`, `core`, `db`, `models`, `repositories`, `schemas`, `services`, `ai`, and `workers`.

---

## Folder Structure
```text
d:\Nebula\
├── alembic/              # Database migration scripts
├── app/                  # FastAPI main application
│   ├── api/              # API endpoints and routing
│   │   └── v1/           # API Version 1 endpoints (auth, health, chat, etc.)
│   ├── core/             # Configuration, security, dependencies, and logging
│   ├── db/               # Database session and base classes
│   ├── models/           # SQLAlchemy DB Models
│   ├── repositories/     # Data Access Layer (DAL)
│   ├── schemas/          # Pydantic schemas (validation/serialization)
│   ├── services/         # Business service layers (e.g. Redis client, mock helpers)
│   ├── ai/               # AI Orchestrator and tools scaffold
│   ├── workers/          # Background celery worker scaffold
│   └── utils/            # Helper functions
├── Dockerfile            # Container configuration
├── docker-compose.yml    # Development multi-container orchestration
├── requirements.txt      # Pinned Python dependencies
├── pyproject.toml        # Ruff, mypy linting configuration
├── .env.example          # Environment variables template
└── README.md             # Developer guidelines (this file)
```

---

## Local Setup

### Prerequisites
- Docker & Docker Compose
- Python 3.13 (optional, if running locally without Docker)

### Running with Docker (Recommended)
1. Copy the environment file template:
   ```bash
   cp .env.example .env
   ```
2. Start all services using Docker Compose:
   ```bash
   docker compose up --build -d
   ```
3. Run Alembic migrations:
   ```bash
   docker compose exec web alembic upgrade head
   ```
4. Access Swagger documentation at `http://localhost:8000/docs`.

### Running Locally
1. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up environment variables in `.env` (pointing to local PostgreSQL and Redis servers).
4. Run migrations:
   ```bash
   alembic upgrade head
   ```
5. Run the FastAPI development server:
   ```bash
   uvicorn app.main:app --reload
   ```

---

## Verification & API Endpoints

- **Health Check:** `GET /api/v1/health`
- **Register User:** `POST /api/v1/auth/register`
- **Login User:** `POST /api/v1/auth/token`
- **Chat Scaffold:** `POST /api/v1/chat`
- **Webhook Endpoint:** `POST /api/v1/webhook` (and GET for verification)
