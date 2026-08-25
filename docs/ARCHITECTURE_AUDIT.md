# Architecture Observations

The repository follows a recognizable FastAPI modular folder layout, but it does not yet implement Clean Architecture consistently. The API layer often owns business workflows, persistence, authorization decisions, provider selection, and transaction commits. Several service objects instantiate their own dependencies, and many infrastructure concerns are global singletons.

The current architecture is best described as a layered prototype:

- `api/v1`: HTTP routes, request validation, many business rules, direct ORM queries.
- `core`: settings, security, authz, middleware, logging, rate limit, cache, metrics.
- `db`: async SQLAlchemy engine/session.
- `models`: SQLAlchemy ORM.
- `repositories`: partial data-access wrappers.
- `services`: provider clients and selected business services.
- `ai`: orchestration, memory, RAG, tools.
- `workers`: non-Celery in-process task wrapper.
- `plugins`: local dynamic import examples.

# Dependency Graph

Observed dependency flow:

```text
FastAPI app
  -> api/router
    -> api/v1/*
      -> core/authz, core/dependencies, db/session
      -> models/*
      -> repositories/*
      -> services/*
      -> ai/*

ai/orchestrator
  -> models/*
  -> services/llm/*
  -> ai/memory
  -> ai/rag

workflow/engine
  -> models/workflow, models/agent
  -> ai/tools/registry
  -> services/llm/dispatcher
  -> httpx

workers/tasks
  -> db/session
  -> models/message/conversation
  -> services/messaging/dispatcher

services/plugins/loader
  -> filesystem
  -> importlib
  -> ai/tools/registry import, but does not register plugin tools
```

# Layer Violations

## API Layer Performs Business Logic

Examples:

- `app/api/v1/auth.py` performs tenant onboarding, role seeding, invitation creation, refresh rotation, and membership creation directly.
- `app/api/v1/knowledge.py` performs provider lookup, parsing, chunking, embedding, DB persistence, and Qdrant indexing.
- `app/api/v1/messaging.py` performs contact/conversation/message creation before scheduling outbound sends.
- `app/api/v1/conversation.py` performs assignment, tagging, comment creation, and WebSocket broadcasts.

Impact: Route handlers are hard to test, hard to reuse, and difficult to transactionally reason about.

## Repository Pattern Is Incomplete

Repositories exist for only user, contact, conversation, and tag. Most models are accessed directly from APIs and services.

Impact: Persistence is not abstracted consistently and cannot be mocked uniformly.

## Domain and Infrastructure Are Coupled

Examples:

- `AIOrchestrator` directly queries SQLAlchemy models and instantiates memory/RAG services.
- Tool implementations accept raw `db` and `business_id` kwargs.
- Workflow engine directly calls LLM providers, tools, and arbitrary HTTP webhooks.

Impact: Business behavior cannot be run independently of infrastructure.

## Globals and Direct Instantiation

Examples:

- Global `settings`, `redis_service`, `metrics`, `manager`, and route-level `ToolRegistry`.
- Direct `httpx.AsyncClient()` inside providers and tools.

Impact: Reduced testability, poor control over lifecycle, and harder multi-process behavior.

# Circular Dependency Risk

No hard Python import cycle was proven by `compileall`, but there are high-risk dependency patterns:

- Models reference one another heavily through string relationships and broad `app.models.__init__` imports.
- Plugin loader imports `ToolRegistry`, while plugin code can import app services.
- AI, workflow, tools, and services cross-reference each other in multiple directions.

Recommended verification: add an import graph tool such as `pydeps` or `grimp` to CI.

# SOLID Review

Single Responsibility: Weak. API routes and `WorkflowEngine.execute_run` own too many responsibilities.

Open/Closed: Partial. Tool and provider interfaces exist, but plugin tools are not integrated and workflow node types require editing a large conditional method.

Liskov Substitution: Partial. Provider interfaces are simple, but concrete clients return provider-specific assumptions and raise raw HTTP errors.

Interface Segregation: Partial. Some interfaces exist, but service abstractions are missing for queues, storage, auth, tenant context, and audit.

Dependency Inversion: Weak. High-level orchestration depends on concrete SQLAlchemy, Qdrant, HTTPX, globals, and direct constructors.

# Clean Architecture Assessment

Status: Partial

The project has folders named like a layered system, but dependency direction is not clean. Domain behavior depends on frameworks and infrastructure. API handlers contain use cases. Persistence and provider concerns leak into orchestration logic.

# Scalability Concerns

- In-memory rate limiting will not work across multiple workers or pods.
- In-memory WebSocket manager will not broadcast across replicas.
- In-memory metrics are process-local and reset on restart.
- FastAPI `BackgroundTasks` is not durable and cannot guarantee message delivery.
- Workflow execution uses `asyncio.create_task` and request-scoped DB sessions.
- No DB indexes for several tenant-filtered access paths.
- Webhook processing loads all WhatsApp integrations to find a matching phone number.
- No queue backpressure, retry, dead-letter handling, or idempotency layer.
- Qdrant connection is hardcoded and collection creation is ad hoc.

# Suggested Improvements

1. Introduce explicit use-case/service classes for onboarding, auth, conversations, messaging, knowledge ingestion, workflows, and agent orchestration.
2. Move all direct ORM work out of API routes except trivial reads.
3. Define repository interfaces or query services for every aggregate used by routes/services.
4. Add a unit-of-work/transaction boundary so commits are controlled at use-case level.
5. Replace in-process background work with Celery/RQ/Arq and durable queues.
6. Move rate limiting, cache, WebSocket fanout, and workflow scheduling to Redis-backed implementations.
7. Add settings for Qdrant, CORS, webhook secrets, token policy, storage, queue broker, and provider URLs.
8. Add Alembic revisions and migration validation in CI.
9. Add typed service protocols for LLM, embedding, vector store, object storage, HTTP client, queue, and clock.
10. Split `WorkflowEngine.execute_run` into node handler classes or a registry.
11. Connect plugin loading to an explicit plugin/tool registration contract with sandboxing and signature validation.
12. Add import graph, ruff, mypy, pytest, and migration checks to CI.

# Future Scalability Concerns

Multi-tenant SaaS scale will require:

- Strong tenant scoping at database query and authorization layers.
- Tenant-aware rate limits and quotas.
- Encrypted credentials and secrets rotation.
- Durable event ingestion for WhatsApp/webhooks.
- Idempotency keys for external events and outgoing messages.
- Horizontal WebSocket fanout through Redis pub/sub or a managed realtime service.
- Queue-based AI/workflow execution with retries and cancellation.
- Observability with traces, histograms, and correlation IDs across async tasks.
- Cost controls for AI calls and embeddings.
