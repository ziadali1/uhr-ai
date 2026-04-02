# Codebase Concerns

## Security

- **HIGH** — Unauthenticated emergency profile endpoint exposes full PHI (medications, allergies, complaints) by UUID with no auth check
- **HIGH** — Mock auth bypass defaults to `true` — if `USE_MOCK=true` in production, all auth is skipped
- **HIGH** — Cached `_use_mock` flag in search service: once set, cannot be toggled without restart
- **HIGH** — Service-role Supabase key used for all DB operations with no Row Level Security (RLS) policies enforced
- **MEDIUM** — Broad-scope storage connection string grants access beyond the intended bucket
- **MEDIUM** — PII (patient names, DOB) present in mock OCR text committed to repo

## Technical Debt

- **HIGH** — `_llm_analysis` raises `NotImplementedError` in production code path
- **HIGH** — Silent 12,000-char LLM input truncation with no warning to caller or user
- **HIGH** — Anonymizer pipeline is never called during document upload — PII stored in plain text in the database
- **MEDIUM** — `file_type` hardcoded to `"pdf"` regardless of actual uploaded file type
- **LOW** — Legacy `blob_url` empty-string field still written on every document record

## Scalability

- **HIGH** — In-memory mock stores lost on restart and incompatible with multi-instance deployments
- **MEDIUM** — No pagination on document listing — full table scan on every request
- **MEDIUM** — Full document scan to build emergency profile on every request (no caching)
- **LOW** — Hardcoded `top_k=3` in RAG retrieval with no config override

## Reliability

- **HIGH** — No retry logic on any Azure service call (OCR, OpenAI) — single transient failure fails the request
- **HIGH** — RAG re-indexing failures silently swallowed — document appears uploaded but is unsearchable
- **MEDIUM** — `StructuredResult` parse errors silently dropped, returning empty results
- **MEDIUM** — SSE streaming ignores client disconnects — server continues processing orphaned requests
- **LOW** — Mock `generate_json` returns `"{}"` — silent empty response in mock mode

## Maintainability

- **HIGH** — Next.js middleware is non-functional in production (static export ignores middleware)
- **MEDIUM** — `_use_mock()` copy-pasted across 8 service files — no central mock toggle
- **MEDIUM** — Allergy severity detection scans full document text globally (not scoped to allergy section)
- **LOW** — React list keys use array index instead of stable IDs
- **LOW** — Missing `FRONTEND_URL` CORS warning when env var is absent

## Missing Infrastructure

- **HIGH** — Zero automated tests despite test dependencies present in requirements.txt
- **HIGH** — No error monitoring or alerting (no Sentry, no structured error logging)
- **HIGH** — No rate limiting on any paid API endpoints (OCR, LLM calls)
- **MEDIUM** — CI pipeline deploys without running tests
- **MEDIUM** — No database migration tooling — schema changes applied manually
