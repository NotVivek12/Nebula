# Critical Debt

Priority: Critical

Task: Create real Alembic migrations for all models.

Reason: The schema cannot be deployed or evolved safely.

Estimated effort: 1-2 days.

Dependencies: Finalize model constraints and indexes.

---

Priority: Critical

Task: Fix authorization permission seeding.

Reason: Onboarded owners lack `knowledge:*`, `agents:*`, and `integrations:*`; `/tool` uses `integrations:*` while seeding `tools:*`.

Estimated effort: 0.5-1 day.

Dependencies: Define canonical permission taxonomy.

---

Priority: Critical

Task: Secure WebSockets.

Reason: Any client can subscribe to any tenant UUID.

Estimated effort: 1 day.

Dependencies: Token-auth handshake and tenant membership dependency for WebSockets.

---

Priority: Critical

Task: Add webhook signature verification and idempotency.

Reason: Current webhook ingestion accepts unverified payloads and can duplicate processing.

Estimated effort: 1-2 days.

Dependencies: Meta app secret/settings and event ID strategy.

---

Priority: Critical

Task: Replace hardcoded/default production secrets.

Reason: Default JWT and webhook secrets are insecure.

Estimated effort: 0.5 day.

Dependencies: Environment validation policy.

---

Priority: Critical

Task: Fix workflow engine runtime failure and unsafe async execution.

Reason: `selectinload` is undefined and request-scoped DB sessions are used in background tasks.

Estimated effort: 1-2 days.

Dependencies: Queue/session lifecycle decision.

# High Debt

Priority: High

Task: Add automated tests.

Reason: No tests exist for auth, tenancy, APIs, models, workflows, tools, RAG, or webhooks.

Estimated effort: 1-3 weeks.

Dependencies: Test database/Redis fixtures and dependency injection cleanup.

---

Priority: High

Task: Implement durable background workers.

Reason: Current worker code is not Celery and FastAPI background tasks are not durable.

Estimated effort: 2-4 days.

Dependencies: Broker settings, worker container, retry policy.

---

Priority: High

Task: Encrypt integration credentials.

Reason: API keys and access tokens are stored as plaintext JSONB.

Estimated effort: 2-4 days.

Dependencies: Key management and migration.

---

Priority: High

Task: Move business logic out of route handlers.

Reason: APIs are hard to test and violate separation of concerns.

Estimated effort: 1-2 weeks.

Dependencies: Use-case/service boundaries.

---

Priority: High

Task: Make RAG consistent.

Reason: Upload/search use Qdrant, but conversational AI uses keyword DB lookup.

Estimated effort: 2-5 days.

Dependencies: Vector store abstraction and provider injection.

---

Priority: High

Task: Harden tool execution.

Reason: Tool args are shallowly validated and HTTP tool allows arbitrary outbound requests.

Estimated effort: 2-4 days.

Dependencies: JSON Schema validation, allowlists, egress policy.

---

Priority: High

Task: Fix strict typing failures.

Reason: `mypy --strict` reports 88 errors; some indicate real defects.

Estimated effort: 3-7 days.

Dependencies: Type policy and SQLAlchemy typing conventions.

# Medium Debt

Priority: Medium

Task: Fix lint failures.

Reason: `ruff` reports 559 issues, including unused imports, complexity, long lines, import ordering, and undefined names.

Estimated effort: 2-5 days.

Dependencies: Decide whether to keep strict ruff profile.

---

Priority: Medium

Task: Add database constraints and indexes.

Reason: Tenant queries, uniqueness, status integrity, and relationships are weakly enforced.

Estimated effort: 2-4 days.

Dependencies: Migration creation.

---

Priority: Medium

Task: Replace in-memory rate limiter/cache/metrics.

Reason: Current implementations are not multi-process or multi-replica safe.

Estimated effort: 3-5 days.

Dependencies: Redis strategy and metrics library.

---

Priority: Medium

Task: Implement real integration management.

Reason: Connectors are mostly simulated and no API manages/test connections.

Estimated effort: 1-3 weeks.

Dependencies: OAuth and credential encryption.

---

Priority: Medium

Task: Improve file and website ingestion safety.

Reason: Uploads lack size/type/malware controls and website parsing has SSRF risk.

Estimated effort: 3-5 days.

Dependencies: Storage, network allow/deny lists, parser libraries.

---

Priority: Medium

Task: Make plugin architecture real.

Reason: Plugins only load lifecycle hooks and do not register tools/actions safely.

Estimated effort: 1-2 weeks.

Dependencies: Plugin manifest spec, signing/sandboxing, registry contract.

# Low Debt

Priority: Low

Task: Remove committed cache artifacts.

Reason: `__pycache__`, `.mypy_cache`, and `.ruff_cache` should not be in source artifacts.

Estimated effort: 0.5 day.

Dependencies: `.gitignore` enforcement.

---

Priority: Low

Task: Update stale docs.

Reason: README references `/auth/register` and a production-ready state that the code does not support.

Estimated effort: 0.5-1 day.

Dependencies: Finalized API contract.

---

Priority: Low

Task: Normalize route naming.

Reason: Singular route prefixes are inconsistent with common REST conventions.

Estimated effort: 1 day.

Dependencies: API versioning/deprecation policy.

---

Priority: Low

Task: Add docstrings only where useful and remove misleading comments.

Reason: Some comments claim Redis-backed or production behavior that is not implemented.

Estimated effort: 0.5-1 day.

Dependencies: None.
