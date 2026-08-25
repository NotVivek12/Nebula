# Security Audit

Audit date: 2026-07-27

Overall security status: Not production-ready.

# Authentication

Status: Partial

Findings:

- JWT login exists in `app/api/v1/auth.py`.
- Password hashing uses bcrypt.
- `get_current_user` decodes JWT and loads the user.
- `User.is_active` is not checked.
- No account lockout, MFA, email verification, password reset, password policy, or login rate limit by account.
- Refresh tokens are stored as raw database values.

Recommendations:

- Check `is_active` on every authenticated request.
- Hash refresh tokens before storage.
- Add logout/revoke-all-sessions endpoints.
- Add password policy and brute-force protection.
- Add issuer, audience, token ID, and scopes/permissions to JWTs.

# JWT

Status: Partial

Findings:

- Uses HS256 and `SECRET_KEY`.
- Default secret is `change_this_to_a_secure_random_key_in_production`.
- No issuer/audience validation.
- No key rotation support.
- No revocation check for access tokens.

Recommendations:

- Fail startup in production if default secret is used.
- Add `iss`, `aud`, `jti`, and explicit token type claims.
- Consider asymmetric signing or managed key rotation for SaaS.

# Secrets

Status: Poor

Findings:

- `.env.example` and `app/core/config.py` contain insecure defaults.
- PostgreSQL defaults are `postgres/postgres`.
- WhatsApp verify token default is predictable.
- Integration credentials are stored in plaintext JSONB.

Recommendations:

- Validate required secrets in production.
- Store integration credentials encrypted with envelope encryption.
- Use Kubernetes Secrets or a secret manager, not ConfigMaps, for sensitive values.
- Redact secrets in logs.

# Permissions and RBAC

Status: Partial

Findings:

- RBAC models and `RequirePermission` exist.
- Onboarding seeds incomplete permissions.
- Permission names are inconsistent between seeded values and route requirements.
- WebSockets bypass auth/RBAC entirely.
- Assignment endpoints do not verify assigned user membership.

Recommendations:

- Define a canonical permission registry and seed all required permissions.
- Add tests proving owner/admin/member access.
- Authenticate WebSockets and verify business membership before accepting.
- Validate target user IDs against tenant membership.

# Input Validation

Status: Weak

Findings:

- Many Pydantic schemas use plain strings/dicts with no constraints.
- Workflow definitions are arbitrary JSON.
- Tool arguments only check required fields, not types or allowed formats.
- URLs accepted by website parser, HTTP tool, and workflow webhook node are unrestricted.
- Uploads lack file size, file type, and content scanning.

Recommendations:

- Add constrained types, enums, length limits, and URL validation.
- Validate workflows with a formal schema.
- Add JSON Schema validation for tool args.
- Apply allowlists or egress proxy policy for outbound URLs.
- Enforce upload limits and malware scanning.

# SQL Injection

Status: Mostly acceptable, with caveats

Findings:

- Most DB access uses SQLAlchemy query construction.
- `ilike(f"%{search_query}%")` is parameterized by SQLAlchemy, not raw SQL.
- No raw user-composed SQL was found.

Recommendations:

- Continue avoiding raw SQL.
- Add query limits everywhere.
- Add indexes for common filters to reduce denial-of-service risk.

# XSS

Status: Unable to verify fully

Findings:

- Backend stores arbitrary message content, website content, tool responses, and internal comments.
- No frontend exists in this repo, so rendering safety cannot be verified.

Recommendations:

- Treat all stored content as untrusted.
- Escape/sanitize in any future frontend.
- Mark internal/system-generated content explicitly.

# CSRF

Status: Mostly not applicable currently

Findings:

- API uses bearer tokens rather than cookies.
- CORS is fully open with credentials allowed.

Recommendations:

- Restrict CORS origins.
- If cookies are added later, implement CSRF protection and SameSite policies.

# Rate Limiting

Status: Partial / not production-safe

Findings:

- Rate limit middleware exists.
- It is in-memory per process despite claiming Redis-backed behavior.
- It keys only by client IP, not tenant/user/token/endpoint.

Recommendations:

- Implement Redis-backed distributed rate limiting.
- Add per-tenant and per-user quotas.
- Exclude only safe health endpoints.

# Webhook Verification

Status: Missing

Findings:

- WhatsApp GET verify token handshake exists.
- POST webhook signature verification is absent.
- No replay/idempotency protection exists.

Recommendations:

- Verify Meta `X-Hub-Signature-256` using app secret.
- Store provider event/message IDs and handle duplicates idempotently.
- Reject malformed payloads explicitly.

# Logging

Status: Partial

Findings:

- Structured logging exists.
- Logs include emails, provider responses, URLs, and errors.
- No systematic redaction layer exists.

Recommendations:

- Redact tokens, API keys, passwords, webhook payload secrets, and PII.
- Include request ID, tenant ID, user ID, and operation IDs consistently.
- Avoid logging full third-party responses.

# Data Isolation and Multi-Tenancy

Status: Partial

Findings:

- Most HTTP routes require membership and check business IDs.
- Webhook tenant resolution depends on WhatsApp phone number ID lookup.
- WebSockets are unauthenticated.
- Some cross-tenant target IDs are not fully validated.
- No database row-level security exists.

Recommendations:

- Add tenant isolation tests for every endpoint.
- Consider PostgreSQL RLS for defense in depth.
- Ensure every model query is tenant-scoped where applicable.
- Authenticate and authorize realtime channels.

# SSRF and Egress Risk

Status: High risk

Findings:

- `parse_website` fetches arbitrary URLs.
- `HTTPRequestTool` calls arbitrary GET/POST URLs.
- Workflow `Webhook` node calls arbitrary URLs.

Recommendations:

- Block private IP ranges, metadata services, localhost, and internal DNS.
- Use allowlists per tenant/integration.
- Route outbound requests through a controlled egress service.
- Add request size/time limits and response truncation everywhere.

# Production Security Recommendations

1. Block production startup with default secrets.
2. Add Alembic migrations and schema constraints before any deployment.
3. Implement webhook signature verification.
4. Encrypt integration credentials.
5. Secure WebSockets.
6. Replace in-memory rate limiting with Redis.
7. Add tenant-isolation tests.
8. Add dependency scanning and CI checks.
9. Add audit trails for auth, RBAC, integration changes, and admin actions.
10. Add safe outbound HTTP policy for tools, workflows, and website ingestion.
