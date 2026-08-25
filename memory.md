# Nebula - Project Memory

This file serves as a persistent record of the architectural decisions, design choices, file structures, and code modifications applied to the Nebula Backend Foundation codebase.

## 2026-07-27

### Initial Setup & Configurations
- **[NEW] [requirements.txt](file:///d:/Nebula/requirements.txt):** Pinned production and development dependencies (FastAPI, SQLAlchemy, asyncpg, Alembic, Redis, structlog, pyjwt, bcrypt, pydantic-settings, ruff, mypy, pytest).
- **[NEW] [pyproject.toml](file:///d:/Nebula/pyproject.toml):** Configured strict code analysis rules (mypy 3.13 configuration, ruff lint selectors).
- **[NEW] [.env.example](file:///d:/Nebula/.env.example):** Defined a configuration schema template containing environment variables for DB, Cache, Security keys, and API paths.
- **[NEW] [.gitignore](file:///d:/Nebula/.gitignore):** Added patterns for python caches, local environment overrides, credentials, IDE files, and Docker volumes.
- **[NEW] [README.md](file:///d:/Nebula/README.md):** Authored detailed onboarding documentation covering direct and Dockerized executions.
- **[NEW] [Dockerfile](file:///d:/Nebula/Dockerfile):** Authored a multi-stage Python 3.13 image compilation pipeline.
- **[NEW] [docker-compose.yml](file:///d:/Nebula/docker-compose.yml):** Orchestrated FastAPI server, PostgreSQL 17-alpine, and Redis 7-alpine with storage volume mounts and automated service readiness health checks.

### Core & Infrastructure Layer
- **[NEW] [app/core/config.py](file:///d:/Nebula/app/core/config.py):** Validated system configurations using Pydantic Settings and computed dynamic service URI connections.
- **[NEW] [app/core/logging.py](file:///d:/Nebula/app/app/core/logging.py):** Initialized `structlog` for structured JSON formatted stdout streams.
- **[NEW] [app/core/security.py](file:///d:/Nebula/app/core/security.py):** Authored password hashing routines using raw `bcrypt` (bypassing deprecated passlib) and signing/decoding of JWT tokens using `pyjwt`.
- **[NEW] [app/db/session.py](file:///d:/Nebula/app/db/session.py):** Configured async session handlers using `create_async_engine` and `async_sessionmaker` for PostgreSQL connectivity.
- **[NEW] [app/services/redis.py](file:///d:/Nebula/app/services/redis.py):** Implemented client state connection management wrapper and health pings.
- **[NEW] [app/main.py](file:///d:/Nebula/app/main.py):** Configured the main FastAPI app, unified lifespan manager, CORS middleware, global exception handler wrappers, and structured telemetry middlewares.

### Domain Database Models
- **[NEW] [app/models/base.py](file:///d:/Nebula/app/models/base.py):** Formulated general model base class alongside UUID primary keys and timestamp tracking mixins.
- **[NEW] [app/models/business.py](file:///d:/Nebula/app/models/business.py):** Defined tenant profile mapping properties.
- **[NEW] [app/models/user.py](file:///d:/Nebula/app/models/user.py):** Map admin/staff access criteria.
- **[NEW] [app/models/contact.py](file:///d:/Nebula/app/models/contact.py):** Mapped customer details, statuses, and custom dictionary contexts (using JSONB).
- **[NEW] [app/models/conversation.py](file:///d:/Nebula/app/models/conversation.py):** Defined tracking fields for active messaging sessions.
- **[NEW] [app/models/message.py](file:///d:/Nebula/app/models/message.py):** Detailed records of text content and channel statuses.
- **[NEW] [app/models/agent.py](file:///d:/Nebula/app/models/agent.py):** Structured custom prompts and dynamic model mappings.
- **[NEW] [app/models/knowledge.py](file:///d:/Nebula/app/models/knowledge.py):** Mapped storage specifications, text segments, and vector embedding float arrays.
- **[NEW] [app/models/workflow.py](file:///d:/Nebula/app/models/workflow.py):** Formulated state parameters and runs execution tables.
- **[NEW] [app/models/integration.py](file:///d:/Nebula/app/models/integration.py):** Created credentials stores for external platforms.
- **[NEW] [app/models/audit.py](file:///d:/Nebula/app/models/audit.py):** Documented history log mappings for admin transactions.
- **[NEW] [app/models/__init__.py](file:///d:/Nebula/app/models/__init__.py):** Tied all models together under the Base class.

### Repositories, Schemas & Dependencies
- **[NEW] [app/repositories/base.py](file:///d:/Nebula/app/repositories/base.py):** Implemented generic repository patterns containing generic CRUD actions.
- **[NEW] [app/repositories/user.py](file:///d:/Nebula/app/repositories/user.py):** Configured user-specific querying functions. Corrected query result processing to use `scalar_one_or_none`.
- **[NEW] [app/repositories/__init__.py](file:///d:/Nebula/app/repositories/__init__.py):** Exported database access repositories.
- **[NEW] [app/schemas/user.py](file:///d:/Nebula/app/schemas/user.py):** Authored schemas for serialization of user onboarding actions.
- **[NEW] [app/schemas/auth.py](file:///d:/Nebula/app/schemas/auth.py):** Authored JWT authentication exchange contracts.
- **[NEW] [app/schemas/health.py](file:///d:/Nebula/app/schemas/health.py):** Set health-check serialization formats.
- **[NEW] [app/schemas/__init__.py](file:///d:/Nebula/app/schemas/__init__.py):** Exported application schemas.
- **[NEW] [app/core/dependencies.py](file:///d:/Nebula/app/core/dependencies.py):** Authored `get_current_user` dependencies.

### Version 1 API Routes
- **[NEW] [app/api/v1/auth.py](file:///d:/Nebula/app/api/v1/auth.py):** Provided user registration `/register` and login `/token` endpoints.
- **[NEW] [app/api/v1/health.py](file:///d:/Nebula/app/api/v1/health.py):** Formulated health verification checking databases and caches.
- **[NEW] [app/api/v1/messaging.py](file:///d:/Nebula/app/api/v1/messaging.py):** Scaffolded webhook receiver verification handshake and message transmission endpoints.
- **[NEW] [app/api/v1/chat.py](file:///d:/Nebula/app/api/v1/chat.py):** Scaffolded conversational routes.
- **[NEW] [app/api/v1/knowledge.py](file:///d:/Nebula/app/api/v1/knowledge.py):** Scaffolded document uploading and semantic query routes.
- **[NEW] [app/api/v1/workflow.py](file:///d:/Nebula/app/api/v1/workflow.py):** Scaffolded workflow invocation routes.
- **[NEW] [app/api/v1/tool.py](file:///d:/Nebula/app/api/v1/tool.py):** Scaffolded tool execution routes.
- **[NEW] [app/api/v1/conversation.py](file:///d:/Nebula/app/api/v1/conversation.py):** Scaffolded session detail routes.
- **[NEW] [app/api/v1/contact.py](file:///d:/Nebula/app/api/v1/contact.py):** Scaffolded contact profile retrieval routes.
- **[NEW] [app/api/router.py](file:///d:/Nebula/app/api/router.py):** Compiled API routing namespaces.
- **[NEW] [app/api/__init__.py](file:///d:/Nebula/app/api/__init__.py) & [app/api/v1/__init__.py](file:///d:/Nebula/app/api/v1/__init__.py):** Marks package structure.

### Package Scaffolds
- **[NEW] [app/ai/__init__.py](file:///d:/Nebula/app/ai/__init__.py):** Marks package structure.
- **[NEW] [app/ai/orchestrator.py](file:///d:/Nebula/app/ai/orchestrator.py):** Added prompt construction and LLM logic placeholders.
- **[NEW] [app/ai/planner.py](file:///d:/Nebula/app/ai/planner.py):** Added tools selection placeholders.
- **[NEW] [app/ai/memory.py](file:///d:/Nebula/app/ai/memory.py):** Added context memory extraction placeholders.
- **[NEW] [app/ai/rag.py](file:///d:/Nebula/app/ai/rag.py):** Added search service placeholders.
- **[NEW] [app/ai/tools/__init__.py](file:///d:/Nebula/app/ai/tools/__init__.py):** Marks package structure.
- **[NEW] [app/ai/tools/base.py](file:///d:/Nebula/app/ai/tools/base.py):** Standardized standard tool template classes.
- **[NEW] [app/workers/__init__.py](file:///d:/Nebula/app/workers/__init__.py):** Marks package structure.
- **[NEW] [app/workers/tasks.py](file:///d:/Nebula/app/workers/tasks.py):** Configured Celery background runner tasks placeholders.
- **[NEW] [app/utils/__init__.py](file:///d:/Nebula/app/utils/__init__.py):** Marks package structure.
- **[NEW] [app/utils/uuid.py](file:///d:/Nebula/app/utils/uuid.py):** Implemented verification tests for UUID4 structures.

### Migrations Setup
- **[NEW] [alembic.ini](file:///d:/Nebula/alembic.ini):** Configured Alembic environments (console logger outputs, prepend python paths).
- **[NEW] [alembic/script.py.mako](file:///d:/Nebula/alembic/script.py.mako):** Established migration code layout blueprint.
- **[NEW] [alembic/env.py](file:///d:/Nebula/alembic/env.py):** Configured async schema migrations to apply mapping operations over database connection pools.

### Code Quality & Corrections
- **[FIX] [app/repositories/base.py](file:///d:/Nebula/app/repositories/base.py):** Resolved a syntax error by pruning accidental stray markdown syntax from the end of the file.

### Verification
- **[VERIFY] Syntax Compilation:** Successfully validated that all Python files compile cleanly with no syntax errors via `python -m compileall app`.

### Phase 2: Multi-Tenancy & Auth Models
- **[MODIFY] [app/models/user.py](file:///d:/Nebula/app/models/user.py):** Decoupled users globally and established relationships linking user instances to memberships and refresh tokens.
- **[MODIFY] [app/models/business.py](file:///d:/Nebula/app/models/business.py):** Updated tenant mapping relationships to use business memberships and user invitation records.
- **[NEW] [app/models/role.py](file:///d:/Nebula/app/models/role.py):** Formulated roles, permissions, and `role_permissions` join table mappings to support RBAC configurations.
- **[NEW] [app/models/business_user.py](file:///d:/Nebula/app/models/business_user.py):** Created business-user association (join) table to model organization memberships.
- **[NEW] [app/models/invitation.py](file:///d:/Nebula/app/models/invitation.py):** Standardized user invitations mapping table for tenant onboarding.
- **[NEW] [app/models/refresh_token.py](file:///d:/Nebula/app/models/refresh_token.py):** Added database representation of user refresh tokens.
- **[MODIFY] [app/models/__init__.py](file:///d:/Nebula/app/models/__init__.py):** Tied all models together under the Base class.

### Phase 2: Core Authorization Guards
- **[NEW] [app/core/authz.py](file:///d:/Nebula/app/core/authz.py):** Implemented multi-tenant dependency utilities, active tenant business identifier extraction from headers, membership security verification, and dynamic permission/role checkers (`RequirePermission`, `RequireRole`).

### Phase 2: Onboarding & Authentication Services
- **[MODIFY] [app/schemas/](file:///d:/Nebula/app/schemas/):** Updated serialization formats in `user.py` (added `BusinessOnboard`), `auth.py` (added `TokenRefreshRequest` and refresh metadata), and created `invitation.py` for team invitation validations.
- **[MODIFY] [app/api/v1/auth.py](file:///d:/Nebula/app/api/v1/auth.py):** Replaced standalone credentials registration with complete tenant onboarding procedures, seeding default roles/permissions, rotation of refresh tokens, secure invitation dispatching, and acceptance workflows.

### Phase 2: Route Protection & Tenant Boundaries
- **[MODIFY] [app/api/v1/](file:///d:/Nebula/app/api/v1/):** Secured all active version 1 endpoints (`messaging.py`, `chat.py`, `knowledge.py`, `workflow.py`, `tool.py`, `conversation.py`, `contact.py`) by wrapping handlers with `RequirePermission` dependency injections to ensure strict tenant boundaries.

### Phase 2: Verification
- **[VERIFY] Syntax Compilation:** Successfully validated that all new and updated files compile cleanly with no syntax errors via `python -m compileall app`.

### Phase 3: Meta WhatsApp Integration Models
- **[NEW] [app/models/webhook_event.py](file:///d:/Nebula/app/models/webhook_event.py):** Added database schema to persist raw webhook payloads for auditing and tracking.
- **[MODIFY] [app/models/__init__.py](file:///d:/Nebula/app/models/__init__.py):** Registered the new `WebhookEvent` mapping in declarative metadata.

### Phase 3: Messaging Providers & Utilities
- **[NEW] [app/services/messaging/base.py](file:///d:/Nebula/app/services/messaging/base.py):** Authored the abstract messaging provider interface establishing actions for text, image, document, templates, and buttons transmission.
- **[NEW] [app/services/messaging/whatsapp.py](file:///d:/Nebula/app/services/messaging/whatsapp.py):** Implemented Meta's WhatsApp Cloud API client with httpx POST request pipelines.
- **[NEW] [app/services/messaging/dispatcher.py](file:///d:/Nebula/app/services/messaging/dispatcher.py):** Created dynamic tenant integration lookup mapping database configurations to messaging channels.
- **[NEW] [app/services/messaging/media.py](file:///d:/Nebula/app/services/messaging/media.py):** Authored a binary media streaming service to download user documents/images from Meta endpoints.

### Phase 3: Webhook Processing & Background Queuing
- **[MODIFY] [app/models/message.py](file:///d:/Nebula/app/models/message.py):** Added `provider_message_id` column to map and track sent message statuses.
- **[NEW] [app/services/messaging/webhook_service.py](file:///d:/Nebula/app/services/messaging/webhook_service.py):** Implemented a parse handler that updates contacts, conversations, downloads media, and logs delivery status updates.
- **[MODIFY] [app/workers/tasks.py](file:///d:/Nebula/app/workers/tasks.py):** Formulated an async worker task `send_outgoing_message_task` that dynamically dispatches text, template, or media payloads based on JSON input formats.
- **[MODIFY] [app/core/config.py](file:///d:/Nebula/app/core/config.py):** Added `WHATSAPP_VERIFY_TOKEN` parameters to Pydantic Settings.
- **[NEW] [app/schemas/messaging.py](file:///d:/Nebula/app/schemas/messaging.py):** Defined schemas for outgoing messaging payloads.
- **[MODIFY] [app/api/v1/messaging.py](file:///d:/Nebula/app/api/v1/messaging.py):** Rewrote Meta verification handshakes, centralized webhook receiving, and outgoing message queue triggers.

### Phase 3: Verification
- **[VERIFY] Syntax Compilation:** Successfully validated that all new and updated messaging provider, task queuing, and webhook processing files compile cleanly with no syntax errors via `python -m compileall app`.

### Phase 4: Conversation Engine Models
- **[MODIFY] [app/models/conversation.py](file:///d:/Nebula/app/models/conversation.py):** Added unread tracking counts, custom metadata mappings, and many-to-many tag relationships.
- **[NEW] [app/models/tag.py](file:///d:/Nebula/app/models/tag.py):** Added Tag models and many-to-many `conversation_tags` join table.
- **[MODIFY] [app/models/__init__.py](file:///d:/Nebula/app/models/__init__.py):** Exported Tag models.

### Phase 4: Conversation Engine Validation Schemas
- **[NEW] [app/schemas/conversation.py](file:///d:/Nebula/app/schemas/conversation.py):** Added request/response validation schemas for conversation responses, tagging, and status assignments.
- **[NEW] [app/schemas/contact.py](file:///d:/Nebula/app/schemas/contact.py):** Added request/response validation schemas for customer contact profile edits.
- **[MODIFY] [app/schemas/__init__.py](file:///d:/Nebula/app/schemas/__init__.py):** Exported all new schema classes.

### Phase 4: Conversation Engine Data Repositories
- **[NEW] [app/repositories/conversation.py](file:///d:/Nebula/app/repositories/conversation.py):** Implemented conversation repository featuring multi-tenant search filtering and unread counter resets.
- **[NEW] [app/repositories/contact.py](file:///d:/Nebula/app/repositories/contact.py):** Implemented customer contact data-access lookup methods.
- **[NEW] [app/repositories/tag.py](file:///d:/Nebula/app/repositories/tag.py):** Implemented tag management and lookups.
- **[MODIFY] [app/repositories/__init__.py](file:///d:/Nebula/app/repositories/__init__.py):** Exported all new repositories.

### Phase 4: Webhook Ingestion Service Updates
- **[MODIFY] [app/services/messaging/webhook_service.py](file:///d:/Nebula/app/services/messaging/webhook_service.py):** Updated incoming message handlers to increment the conversation's `unread_count` when a new customer message is parsed.

### Phase 4: Conversation Engine API Controllers
- **[MODIFY] [app/api/v1/conversation.py](file:///d:/Nebula/app/api/v1/conversation.py):** Implemented conversation searching, custom tagging, paginated history loads, unread resets, and lifecycle state changes.
- **[MODIFY] [app/api/v1/contact.py](file:///d:/Nebula/app/api/v1/contact.py):** Implemented customer contact profile retrieval and updates controllers.

### Phase 4: Verification
- **[VERIFY] Syntax Compilation:** Successfully validated that all new and updated conversation engine schemas, repositories, webhook processing, and API route controllers compile cleanly with no syntax errors via `python -m compileall app`.

### Phase 5: AI Orchestration Models
- **[MODIFY] [app/models/agent.py](file:///d:/Nebula/app/models/agent.py):** Added `provider` and `temperature` fields to support multi-provider LLM properties.

### Phase 5: LLM Client Wrappers & Registry Dispatcher
- **[NEW] [app/services/llm/base.py](file:///d:/Nebula/app/services/llm/base.py):** Formulated abstract LLM provider interface targeting async text completions.
- **[NEW] [app/services/llm/openai.py](file:///d:/Nebula/app/services/llm/openai.py):** Implemented OpenAI API wrapper targeting `/v1/chat/completions`.
- **[NEW] [app/services/llm/gemini.py](file:///d:/Nebula/app/services/llm/gemini.py):** Implemented Google Gemini API wrapper targeting `/v1beta/models/...:generateContent`.
- **[NEW] [app/services/llm/anthropic.py](file:///d:/Nebula/app/services/llm/anthropic.py):** Implemented Anthropic Claude API wrapper targeting `/v1/messages`.
- **[NEW] [app/services/llm/openrouter.py](file:///d:/Nebula/app/services/llm/openrouter.py):** Implemented OpenRouter API proxy wrapper.
- **[NEW] [app/services/llm/dispatcher.py](file:///d:/Nebula/app/services/llm/dispatcher.py):** Resolved active tenant LLM integration credentials.

- **[MODIFY] [app/ai/rag.py](file:///d:/Nebula/app/ai/rag.py):** Updated search logic to query database knowledge chunks mapped to the active tenant business.

### Phase 5: AI Prompt Orchestration & Routing
- **[MODIFY] [app/ai/orchestrator.py](file:///d:/Nebula/app/ai/orchestrator.py):** Authored the process pipeline parsing conversation memories, merging dynamic customer profile variables, fetching keyword document chunks, and dispatching tasks to the resolved provider.
- **[NEW] [app/schemas/chat.py](file:///d:/Nebula/app/schemas/chat.py):** Added data schemas validating incoming chat query posts.
- **[MODIFY] [app/schemas/__init__.py](file:///d:/Nebula/app/schemas/__init__.py):** Exported chat validation models.
- **[MODIFY] [app/api/v1/chat.py](file:///d:/Nebula/app/api/v1/chat.py):** Updated route handler to run the orchestrator process and return LLM outputs directly.

### Phase 5: Verification
- **[VERIFY] Syntax Compilation:** Successfully validated that all new and updated AI Orchestration interface wrappers, dispatchers, RAG models, pipelines, and chat API route controllers compile cleanly with no syntax errors via `python -m compileall app`.

### Phase 6: Long-Term AI Memory Models
- **[NEW] [app/models/contact_memory.py](file:///d:/Nebula/app/models/contact_memory.py):** Added the `ContactMemory` model to save tenant-scoped facts, summaries, custom traits, and purchase histories.
- **[MODIFY] [app/models/contact.py](file:///d:/Nebula/app/models/contact.py):** Added relationship links mapping customer Contact profiles to memory logs.
- **[MODIFY] [app/models/__init__.py](file:///d:/Nebula/app/models/__init__.py):** Registered new memory models on the Base class metadata.

### Phase 6: Long-Term AI Memory Services & Prompt Pipelines
- **[MODIFY] [app/ai/memory.py](file:///d:/Nebula/app/ai/memory.py):** Authored `AIMemoryService` containing keyword intersection ranking, LLM conversation summarization, and consolidating pruning filters.
- **[MODIFY] [app/ai/orchestrator.py](file:///d:/Nebula/app/ai/orchestrator.py):** Merged retrieved long-term customer memories into prompt system headers and scheduled background summarization checks.

### Phase 6: Verification
- **[VERIFY] Syntax Compilation:** Successfully validated that all new and updated long-term contact memory schemas, services, and prompt orchestrators compile cleanly with no syntax errors via `python -m compileall app`.

### Phase 7: RAG Knowledge Models
- **[MODIFY] [app/models/knowledge.py](file:///d:/Nebula/app/models/knowledge.py):** Added the `version` column to the `KnowledgeDocument` model.

### Phase 7: Abstract Embedding Providers
- **[NEW] [app/services/embeddings/base.py](file:///d:/Nebula/app/services/embeddings/base.py):** Authored abstract vector embedding generator interface.
- **[NEW] [app/services/embeddings/openai.py](file:///d:/Nebula/app/services/embeddings/openai.py):** Implemented OpenAI embedding REST client.
- **[NEW] [app/services/embeddings/gemini.py](file:///d:/Nebula/app/services/embeddings/gemini.py):** Implemented Gemini embedding REST client.

### Phase 7: Abstract Vector Store
- **[NEW] [app/services/vector_store/base.py](file:///d:/Nebula/app/services/vector_store/base.py):** Authored abstract vector store adapter interface.
- **[NEW] [app/services/vector_store/qdrant.py](file:///d:/Nebula/app/services/vector_store/qdrant.py):** Implemented Qdrant REST client adapter mapping search query filters.

### Phase 7: Document Parsing & Text Chunking
- **[NEW] [app/services/knowledge/parser.py](file:///d:/Nebula/app/services/knowledge/parser.py):** Authored document text extraction utilities supporting text files, CSV formats, website URL scraping, and fallback docx/pdf streams.
- **[NEW] [app/services/knowledge/chunker.py](file:///d:/Nebula/app/services/knowledge/chunker.py):** Authored sliding window splitter with configurable overlapping bounds.

### Phase 7: RAG REST API Controllers & Schemas
- **[NEW] [app/schemas/knowledge.py](file:///d:/Nebula/app/schemas/knowledge.py):** Defined schemas validating RAG similarity requests.
- **[MODIFY] [app/schemas/__init__.py](file:///d:/Nebula/app/schemas/__init__.py):** Exported knowledge search models.
- **[MODIFY] [app/api/v1/knowledge.py](file:///d:/Nebula/app/api/v1/knowledge.py):** Updated routes to parse uploads/webpages, chunk, embed, index points in Qdrant, and fetch ranked contexts.

### Phase 7: Verification
- **[VERIFY] Syntax Compilation:** Successfully validated that all new and updated RAG document parser services, slide window chunkers, abstract embedding wrappers, Qdrant adapters, schemas, and API route controllers compile cleanly with no syntax errors via `python -m compileall app`.

### Phase 8: AI Tool Engine
- **[MODIFY] [app/ai/tools/base.py](file:///d:/Nebula/app/ai/tools/base.py):** Updated base Tool class to include permissions mapping.
- **[NEW] [app/ai/tools/lead.py](file:///d:/Nebula/app/ai/tools/lead.py):** Implemented database contact registration tool.
- **[NEW] [app/ai/tools/email.py](file:///d:/Nebula/app/ai/tools/email.py):** Implemented outbound email simulation tool.
- **[NEW] [app/ai/tools/http.py](file:///d:/Nebula/app/ai/tools/http.py):** Implemented generic outbound HTTP GET/POST API calling tool.
- **[NEW] [app/ai/tools/registry.py](file:///d:/Nebula/app/ai/tools/registry.py):** Implemented central registry holding plugins, performing validation check parameters, RBAC checks, and database audit logs.
- **[MODIFY] [app/ai/tools/__init__.py](file:///d:/Nebula/app/ai/tools/__init__.py):** Exported all tool modules.

### Phase 8: AI Tool Engine API Controllers & Schemas
- **[NEW] [app/schemas/tool.py](file:///d:/Nebula/app/schemas/tool.py):** Defined schemas validating tool run triggers.
- **[MODIFY] [app/schemas/__init__.py](file:///d:/Nebula/app/schemas/__init__.py):** Exported tool run request models.
- **[MODIFY] [app/api/v1/tool.py](file:///d:/Nebula/app/api/v1/tool.py):** Updated routes to list registered plugins and execute tools with validation and RBAC checks.

### Phase 8: Verification
- **[VERIFY] Syntax Compilation:** Successfully validated that all new and updated Tool Engine base classes, concrete plugin tools (CreateLead, SendEmail, HTTPRequest), central registry executors, schemas, and API route controllers compile cleanly with no syntax errors via `python -m compileall app`.

### Phase 9: Workflow Engine Models
- **[MODIFY] [app/models/workflow.py](file:///d:/Nebula/app/models/workflow.py):** Added execution variables context tracking states and node pointer parameters to `WorkflowRun`. Added `WorkflowNodeLog` model to store sequential execution step logs.
- **[MODIFY] [app/models/__init__.py](file:///d:/Nebula/app/models/__init__.py):** Registered new log models in Base package metadata.

### Phase 9: Workflow Engine Validation Schemas
- **[NEW] [app/schemas/workflow.py](file:///d:/Nebula/app/schemas/workflow.py):** Added request and response validation schemas for workflow definitions, execution run instances, human approval overrides, and node logs.
- **[MODIFY] [app/schemas/__init__.py](file:///d:/Nebula/app/schemas/__init__.py):** Exported new workflow models.

### Phase 9: Workflow Engine Service
- **[NEW] [app/services/workflow/engine.py](file:///d:/Nebula/app/services/workflow/engine.py):** Implemented `WorkflowEngine` handling trigger inputs, condition checking, AI decision routing, tool executor triggers, loop counting, delays scheduling, webhooks calls, and manual approval pauses.

### Phase 9: Workflow Engine API Controllers
- **[MODIFY] [app/api/v1/workflow.py](file:///d:/Nebula/app/api/v1/workflow.py):** Updated route controllers to create workflows, trigger runs, list runs history, retrieve step logs, and manually approve paused approval runs.

### Phase 9: Verification
- **[VERIFY] Syntax Compilation:** Successfully validated that all new and updated Workflow Engine models, execution services (handling all 10 node types), validation schemas, and REST controllers compile cleanly with no syntax errors via `python -m compileall app`.

### Phase 10: Human Support Shared Inbox Models
- **[MODIFY] [app/models/conversation.py](file:///d:/Nebula/app/models/conversation.py):** Appended assignee (`assigned_agent_id`), user relationship mapping, and AI control status toggles.
- **[MODIFY] [app/models/message.py](file:///d:/Nebula/app/models/message.py):** Added internal comment indicator flags (`is_internal`).

### Phase 10: WebSocket Connection Manager
- **[NEW] [app/services/websocket_manager.py](file:///d:/Nebula/app/services/websocket_manager.py):** Authored dynamic room publisher class grouping sockets by tenant UUID and broadcasting updates with strict isolation logic.

### Phase 10: Human Support Validation Schemas
- **[NEW] [app/schemas/human_support.py](file:///d:/Nebula/app/schemas/human_support.py):** Added validation schemas for conversation assignments, comments, and typing indicator signals.
- **[MODIFY] [app/schemas/__init__.py](file:///d:/Nebula/app/schemas/__init__.py):** Exported human support models.

### Phase 10: Human Support API Routes
- **[MODIFY] [app/repositories/conversation.py](file:///d:/Nebula/app/repositories/conversation.py):** Added support for querying conversations by assigned agent status.
- **[MODIFY] [app/api/v1/conversation.py](file:///d:/Nebula/app/api/v1/conversation.py):** Updated search filters to filter by assignees, and implemented assignment takeover/release endpoints, internal comments creation, and typing indicator signals.

### Phase 10: WebSocket Endpoint Gateway
- **[NEW] [app/api/v1/websocket.py](file:///d:/Nebula/app/api/v1/websocket.py):** Implemented multi-tenant WebSocket endpoint channel.
- **[MODIFY] [app/api/router.py](file:///d:/Nebula/app/api/router.py):** Registered the new WebSocket endpoints with the API router stack.

### Phase 10: Verification
- **[VERIFY] Syntax Compilation:** Successfully validated that all new and updated Human Support models, connection managers, REST endpoints, WebSocket routes, schemas, and router assemblies compile cleanly with no syntax errors via `python -m compileall app`.

### Phase 11: AI Agent Collaboration Framework Models
- **[MODIFY] [app/models/agent.py](file:///d:/Nebula/app/models/agent.py):** Added role details, instructions, allowed tools, and RBAC permissions to the `Agent` configuration table. Created `AgentAnalytics` model to capture execution counts, latencies, and success metrics.
- **[MODIFY] [app/models/conversation.py](file:///d:/Nebula/app/models/conversation.py):** Appended `active_agent_id` mapping the active conversation agent pointer.
- **[NEW] [app/models/agent_handoff.py](file:///d:/Nebula/app/models/agent_handoff.py):** Authored handoff audit trail model tracking transfer context.
- **[MODIFY] [app/models/__init__.py](file:///d:/Nebula/app/models/__init__.py):** Registered new agent handoff and analytics models.

### Phase 11: AI Agent Validation Schemas
- **[NEW] [app/schemas/agent.py](file:///d:/Nebula/app/schemas/agent.py):** Added request/response validation schemas for AI agent configuration metadata, handoff logs, and performance analytics logs.
- **[MODIFY] [app/schemas/__init__.py](file:///d:/Nebula/app/schemas/__init__.py):** Exported new AI agent models.

### Phase 11: AI Multi-Agent Orchestrator Service
- **[NEW] [app/services/agent/orchestrator.py](file:///d:/Nebula/app/services/agent/orchestrator.py):** Implemented `MultiAgentOrchestrator` supporting auto-selection, handoff logs tracking, WebSocket broadcasts, agent instructions merging, restricted tools execution scopes, and metrics updates.

### Phase 11: AI Multi-Agent API Routes
- **[NEW] [app/api/v1/agent.py](file:///d:/Nebula/app/api/v1/agent.py):** Implemented REST endpoint controllers to create AI agents, list configurations, manually trigger handoffs, and fetch metrics.
- **[MODIFY] [app/api/router.py](file:///d:/Nebula/app/api/router.py):** Integrated agent router stack.

### Phase 11: Verification
- **[VERIFY] Syntax Compilation:** Successfully validated that all new and updated AI Agent models, handoff tracers, metrics tracking analytics tables, intent selector services, validation schemas, and REST controllers compile cleanly with no syntax errors via `python -m compileall app`.

### Phase 12: Generic Integration Framework
- **[NEW] [app/services/integrations/base.py](file:///d:/Nebula/app/services/integrations/base.py):** Authored third-party connector interface class.
- **[NEW] [app/services/integrations/connectors.py](file:///d:/Nebula/app/services/integrations/connectors.py):** Authored concrete connectors for Google Sheets, Slack, Gmail, Stripe, Calendar, HubSpot, Zoho, Shopify, and Razorpay.

### Phase 12: AI Plugin System
- **[NEW] [app/services/plugins/loader.py](file:///d:/Nebula/app/services/plugins/loader.py):** Authored dynamic loader executing lifecycle hooks (`on_load`, `on_enable`, `on_disable`) and registration mapping of plugins.
- **[NEW] [plugins/slack_alert/](file:///d:/Nebula/plugins/slack_alert/):** Authored an example plugin manifest and entry point logic.

### Phase 12: Telemetry Metrics Logging (Prometheus)
- **[NEW] [app/core/metrics.py](file:///d:/Nebula/app/core/metrics.py):** Authored system metrics recorder tracking LLM tokens consumption, latencies, failures, and executions.
- **[NEW] [app/api/v1/metrics.py](file:///d:/Nebula/app/api/v1/metrics.py):** Implemented Prometheus plain-text endpoint route.
- **[MODIFY] [app/api/router.py](file:///d:/Nebula/app/api/router.py):** Registered the new metrics endpoints with router stack.

### Phase 12: Production Infrastructure Optimization
- **[NEW] [app/core/rate_limit.py](file:///d:/Nebula/app/core/rate_limit.py):** Implemented sliding window API rate limiting middleware.
- **[NEW] [app/core/cache.py](file:///d:/Nebula/app/core/cache.py):** Implemented cache managers providing endpoint result caches decorators.
- **[NEW] [app/core/circuit_breaker.py](file:///d:/Nebula/app/core/circuit_breaker.py):** Implemented circuit breaker objects shielding external downstreams from cascading outages.
- **[MODIFY] [app/main.py](file:///d:/Nebula/app/main.py):** Injected the rate limiter middleware and load plugins calls to lifecycle boots.

### Phase 12: Production Deployment Readiness
- **[NEW] [Dockerfile.prod](file:///d:/Nebula/Dockerfile.prod):** Authored multi-stage optimized production Docker configuration.
- **[NEW] [k8s/deployment.yaml](file:///d:/Nebula/k8s/deployment.yaml):** Created Kubernetes API deployment configs, services, settings maps, and horizontal pod autoscalers (HPA).

### Phase 12: Verification
- **[VERIFY] Syntax Compilation:** Successfully validated that all new and updated Integration connectors (Gmail, Sheets, Slack, HubSpot, Stripe, Zoho, Shopify, Razorpay, Calendar), dynamic plugin loaders, example plugins, Prometheus telemetry modules, rate limits, caching middleware, and app lifecycles compile cleanly with no syntax errors via `python -m compileall app`.
