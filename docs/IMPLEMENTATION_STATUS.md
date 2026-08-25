# Implementation Status

Audit date: 2026-08-25

Status legend:

- `WORKING`: verified from code and/or runtime behavior
- `PARTIAL`: implemented in some form, but incomplete, unsafe, inconsistent, or unverified
- `MISSING`: not present
- `BLOCKED`: cannot be fully verified without missing external credentials/services or additional setup

## Executive Summary

Nebula is currently a broad FastAPI prototype with real code for authentication, tenant-scoped APIs, messaging, AI orchestration, knowledge ingestion, workflows, tools, agents, and plugin loading. It is not production-ready.

The runtime stack can now build and start successfully with Docker Compose, and the health endpoint reports healthy PostgreSQL and Redis dependencies. However, the codebase still has no automated tests, no Alembic revision history, extensive lint and type failures, insecure defaults, incomplete permission seeding, unauthenticated WebSocket access, and a non-durable background processing model.

The most urgent production blockers are:

- no Alembic revision files
- no real test suite
- webhook POST requests do not verify Meta signatures
- webhook ingestion has no idempotency protection
- WebSockets have no authentication or membership checks
- permissions seeded at onboarding do not match several protected routes
- worker execution is in-process and not durable
- local defaults remain insecure

## Baseline Verification

### Environment

- Local Python version: `Python 3.12.6`
- Declared target version in [pyproject.toml](/abs/path/D:/Nebula/pyproject.toml:1): `py313`
- The checkout is not a git worktree: `git status --short` returned `fatal: not a git repository`

### Dependency Installation

- Dependencies are declared in [requirements.txt](/abs/path/D:/Nebula/requirements.txt:1)
- Runtime startup previously failed due to missing `httpx` and `email-validator`; both are now present in the dependency file and the Docker image builds successfully

### Static and Runtime Checks

- `python -m compileall app`: `WORKING`
- `python -m ruff check .`: `FAILED`
  - 559 issues reported
  - includes style issues plus real runtime issues such as undefined `selectinload` in `app/services/workflow/engine.py`
- `python -m mypy app`: `FAILED`
  - 87 errors across 27 files
  - includes type safety issues and real model/logic mismatches
- `python -m pytest`: `FAILED` as a verification gate
  - no tests exist
  - pytest collected `0` items
- `python -m alembic current`: `FAILED`
  - no revision directory exists
  - command attempted database connection and failed local password auth
- Docker build: `WORKING`
- Docker Compose startup: `WORKING`
- `GET http://localhost:8000/api/v1/health`: `WORKING`
  - database healthy
  - redis healthy

## Repository Inspection

### Structure

Verified top-level structure:

- `app/`
- `alembic/`
- `docs/`
- `plugins/`
- `k8s/`
- `Dockerfile`
- `Dockerfile.prod`
- `docker-compose.yml`
- `requirements.txt`
- `pyproject.toml`
- `README.md`

Observed issues:

- committed/generated `__pycache__` and `.pyc` artifacts are present under `app/`
- no `tests/` directory exists
- no CI configuration was found

### Documentation

Status: `PARTIAL`

Findings:

- [README.md](/abs/path/D:/Nebula/README.md:1) overstates readiness and includes stale endpoints such as `/api/v1/auth/register`
- the real auth onboarding endpoint is `/api/v1/auth/onboard`
- existing docs in `docs/` are helpful audit notes, but they are not a substitute for source verification

## Configuration and Secrets

Status: `PARTIAL`

Verified in [app/core/config.py](/abs/path/D:/Nebula/app/core/config.py:1) and [.env](/abs/path/D:/Nebula/.env:1):

- settings are loaded with `BaseSettings`
- database and Redis are configurable
- JSON logging flag exists

Problems:

- insecure default `SECRET_KEY`
- insecure default Postgres credentials
- default WhatsApp verification token in code
- no production startup guard against unsafe defaults
- no JWT issuer, audience, token type, or JTI settings
- no Qdrant, queue broker, object storage, or CORS allowlist settings
- `.env` local database settings point to `localhost`, while Docker Compose overrides app container connectivity via service names

## Docker and Runtime

Status: `PARTIAL`

Verified:

- [docker-compose.yml](/abs/path/D:/Nebula/docker-compose.yml:1) starts `web`, `db`, and `redis`
- [Dockerfile](/abs/path/D:/Nebula/Dockerfile:1) now builds a working app image
- health endpoint reports database and Redis healthy

Problems:

- Compose file still uses obsolete top-level `version`
- PostgreSQL service uses `postgres:17-alpine`, which emits locale warnings at init time
- production image still runs as root
- no worker container exists
- no Qdrant service exists in local orchestration

## Database and Migrations

Status: `PARTIAL`

Verified:

- SQLAlchemy models exist for businesses, users, memberships, roles, contacts, conversations, messages, knowledge, workflows, integrations, webhook events, agents, invitations, refresh tokens, and more
- async database session setup exists in [app/db/session.py](/abs/path/D:/Nebula/app/db/session.py:1)
- Alembic environment exists in [alembic/env.py](/abs/path/D:/Nebula/alembic/env.py:1)

Problems:

- `alembic/versions` directory is missing
- there are no migration revisions
- fresh database creation from migrations is not possible
- Alembic current status cannot report a revision chain because none exists

## Authentication and Authorization

Status: `PARTIAL`

Verified:

- onboarding, login, refresh, invite, and accept-invite routes exist in [app/api/v1/auth.py](/abs/path/D:/Nebula/app/api/v1/auth.py:1)
- password hashing uses bcrypt in [app/core/security.py](/abs/path/D:/Nebula/app/core/security.py:1)
- JWT access token creation and decoding exist
- request membership and permission enforcement exist in [app/core/authz.py](/abs/path/D:/Nebula/app/core/authz.py:1)

Problems:

- access tokens only include `sub`, `iat`, and `exp`
- no JWT issuer, audience, JTI, or token type
- refresh tokens are stored raw
- no logout/revoke session endpoint
- no password policy
- no brute-force protection
- no active-user check in token auth flow
- onboarding seeds only:
  - `contacts:*`
  - `conversations:*`
  - `invitations:*`
  - `workflows:*`
  - `tools:*`
- route protection also expects:
  - `knowledge:*`
  - `agents:*`
  - `integrations:*`
- tool routes use `integrations:read/write`, which is inconsistent with seeded `tools:read/write`

## API Surface

Status: `PARTIAL`

Verified routers in [app/api/router.py](/abs/path/D:/Nebula/app/api/router.py:1):

- `health`
- `auth`
- `messaging`
- `chat`
- `knowledge`
- `workflow`
- `tool`
- `conversation`
- `contact`
- `websocket`
- `agent`
- `metrics`

Problems:

- many routes still contain business logic directly
- route naming is inconsistent, including singular forms such as `/conversation`, `/contact`, `/workflow`, and `/tool`
- some responses are raw dicts instead of stable response models

## Messaging and WhatsApp

Status: `PARTIAL`

Verified:

- webhook GET verification route exists in [app/api/v1/messaging.py](/abs/path/D:/Nebula/app/api/v1/messaging.py:1)
- webhook POST ingestion route exists
- outgoing send route exists
- [app/services/messaging/webhook_service.py](/abs/path/D:/Nebula/app/services/messaging/webhook_service.py:1) resolves business by WhatsApp integration credentials, creates contacts/conversations/messages, and updates delivery statuses
- outgoing provider dispatch exists in [app/workers/tasks.py](/abs/path/D:/Nebula/app/workers/tasks.py:1)

Problems:

- no verification of `X-Hub-Signature-256`
- no webhook idempotency check on inbound provider message IDs
- raw webhook events are persisted, but replay protection is absent
- inbound webhook processing performs persistence directly inside the request path
- no durable queue for inbound AI processing
- no retry or dead-letter framework for outbound sending
- no independent worker deployment
- media download stores local paths rather than durable object storage references

## Background Jobs

Status: `PARTIAL`

Verified:

- [app/workers/tasks.py](/abs/path/D:/Nebula/app/workers/tasks.py:1) creates a fresh DB session internally for outbound send execution

Problems:

- jobs are triggered from FastAPI `BackgroundTasks`, not a durable broker
- Celery is referenced in comments only
- no Celery app, queues, retries, dead-lettering, or worker service
- workflow engine still launches `asyncio.create_task(...)`

## Conversations and Human Support

Status: `PARTIAL`

Verified:

- conversation search, creation, retrieval, message history, status changes, tags, assignment, release, internal comments, and typing routes exist in [app/api/v1/conversation.py](/abs/path/D:/Nebula/app/api/v1/conversation.py:1)
- WebSocket broadcast manager exists

Problems:

- WebSocket endpoint in [app/api/v1/websocket.py](/abs/path/D:/Nebula/app/api/v1/websocket.py:1) has no auth and trusts any `business_id` path parameter
- in-memory WebSocket manager is not horizontally scalable
- no Redis pub/sub fanout
- conversation state model is inconsistent with the target lifecycle described in the product brief

## AI, RAG, Tools, and Agents

Status: `PARTIAL`

Verified:

- provider wrappers exist for OpenAI, Gemini, Anthropic, and OpenRouter
- AI orchestrator exists
- knowledge upload/search routes exist
- tool registry and three tools exist
- agent CRUD/handoff/analytics routes exist

Problems:

- conversational retrieval path is separate from Qdrant semantic search
- tool calling is not integrated into the main conversation pipeline
- HTTP tool allows arbitrary outbound URLs and creates SSRF risk
- website ingestion also uses arbitrary URLs without SSRF protections
- integrations are mostly placeholder implementations
- multi-agent orchestration is not deeply connected to main message processing

## Workflows

Status: `PARTIAL`

Verified:

- workflow create/run/log/approve routes exist
- workflow engine contains node execution logic for multiple node types

Problems:

- workflow execution lives in one large complex method
- `selectinload` is used without import in [app/services/workflow/engine.py](/abs/path/D:/Nebula/app/services/workflow/engine.py:133)
- workflow runtime still uses `asyncio.create_task(...)`
- no durable scheduler or continuation mechanism
- webhook/HTTP workflow steps use unrestricted outbound URLs
- workflow definitions are not robustly schema-validated

## Observability, Rate Limiting, and Cache

Status: `PARTIAL`

Verified:

- structured logging setup exists
- request logging middleware exists
- health endpoint exists
- metrics route exists

Problems:

- rate limiting is process-local
- cache is process-local
- metrics are process-local
- no correlation of tenant ID, conversation ID, tool execution, or AI cost across the main flow
- sensitive-data redaction policy is incomplete

## Testing

Status: `MISSING`

Verified:

- `pytest` collected zero tests
- no `tests/` directory exists

This is currently the single biggest blocker to honest completion claims across all later phases.

## Verified Working Areas

- app imports and runs under Docker
- Docker image builds successfully
- Docker Compose starts `web`, `db`, and `redis`
- health endpoint reports healthy Postgres and Redis
- auth, conversation, messaging, knowledge, workflow, agent, tool, and metrics routers are registered
- Redis connects on startup
- plugin loading runs on app startup

## Verified Broken or Missing Areas

- no Alembic revision history
- no automated tests
- Ruff fails
- Mypy fails
- WebSocket authentication missing
- WhatsApp webhook signature verification missing
- webhook idempotency missing
- distributed queue missing
- local default secrets insecure
- permission seeding incomplete and inconsistent
- SSRF protections missing in HTTP-based features

## Highest-Leverage Next Implementation Slice

Recommended immediate priority after this baseline:

1. Foundation hardening
   - settings validation
   - startup guards for unsafe defaults
   - configurable CORS and JWT settings
   - health/live/ready split
2. Migration foundation
   - generate real Alembic revisions for current schema
3. Security-critical messaging core
   - WhatsApp signature verification
   - webhook idempotency
   - durable enqueue boundary
4. Auth and tenant safety
   - fix permission seeding and naming mismatches
   - secure WebSocket auth and tenant membership verification
5. Test harness
   - establish pytest fixtures for app, database, and Redis

## Honest Readiness Assessment

As of 2026-08-25, Nebula is not production-ready.

It is a partially functioning backend prototype with real runtime behavior, but it still lacks the migration history, security controls, test coverage, durable job infrastructure, and quality gates required for safe production use.
