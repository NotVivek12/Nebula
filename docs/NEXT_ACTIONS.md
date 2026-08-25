# Next Actions

| Priority | Task | Reason | Estimated effort | Dependencies |
|---|---|---|---|---|
| P0 | Add Alembic migrations for the current schema | Database cannot be deployed or verified without revisions | 1-2 days | Confirm model constraints/indexes |
| P0 | Fix permission seeding and naming | New owners cannot access claimed modules such as knowledge, agents, and integrations | 0.5-1 day | Permission taxonomy |
| P0 | Secure WebSocket authentication/authorization | Current endpoint allows arbitrary tenant subscription | 1 day | JWT handshake design |
| P0 | Add WhatsApp webhook signature verification and idempotency | Prevent spoofed webhooks and duplicate processing | 1-2 days | Meta app secret setting |
| P0 | Fix workflow engine runtime/session issues | `selectinload` is undefined and request sessions are used in background tasks | 1-2 days | Worker/session lifecycle |
| P0 | Add production secret validation | Default JWT and webhook secrets are unsafe | 0.5 day | Environment policy |
| P1 | Introduce test suite for auth, RBAC, tenancy, and APIs | No automated verification exists | 1 week initial | Test DB/Redis fixtures |
| P1 | Replace FastAPI background messaging with a real queue/worker | In-process tasks are not durable or retryable | 2-4 days | Celery/RQ/Arq decision |
| P1 | Encrypt integration credentials | Plaintext API keys/tokens are stored in JSONB | 2-4 days | Key management |
| P1 | Refactor API business logic into services/use cases | Current routes are oversized and tightly coupled | 1-2 weeks | Service boundary design |
| P1 | Make conversational RAG use the vector store path | Upload/search and chat retrieval currently disagree | 2-5 days | Vector service injection |
| P1 | Harden tool and workflow outbound HTTP | Arbitrary outbound URLs create SSRF risk | 2-4 days | Egress policy |
| P1 | Fix mypy strict errors | 88 type errors include real defect indicators | 3-7 days | Typing conventions |
| P2 | Add Redis-backed rate limiting and cache | Current implementations are per-process memory only | 3-5 days | Redis key design |
| P2 | Add real metrics instrumentation | `/metrics` exists but counters are mostly unused | 2-4 days | Metrics label policy |
| P2 | Add integration management APIs and real connector implementations | Existing connector classes are mostly simulated | 1-3 weeks | OAuth/credential storage |
| P2 | Validate workflow definitions with schemas | Arbitrary JSON can break runtime execution | 2-4 days | Node schema design |
| P2 | Add file upload controls and safer parsers | Current ingestion is fragile and unsafe | 3-5 days | Storage and scanning choices |
| P3 | Remove cache artifacts from repository | Generated files add noise and should not ship | 0.5 day | None |
| P3 | Update README and docs to match implemented routes | Current docs overclaim production readiness and reference stale endpoints | 0.5-1 day | API contract |
| P3 | Normalize REST route naming | API consistency improves maintainability | 1 day | Versioning policy |
