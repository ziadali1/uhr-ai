# Integrations

**Analysis Date:** 2026-04-02

## Databases

**Supabase (PostgreSQL):**
- Provider: Supabase (managed PostgreSQL)
- Backend client: `supabase-py` 2.4.6 — initialized via `create_client()` in `backend/services/supabase_store.py` and `backend/services/health_store.py`
- Frontend client: `@supabase/ssr` + `@supabase/supabase-js` — browser client initialized in `frontend/lib/supabase.ts` via `createBrowserClient()`
- Auth: backend uses `SUPABASE_SERVICE_ROLE_KEY` (bypasses RLS); frontend uses `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- Connection pattern: lazy singleton `_client: Client | None = None` instantiated on first use
- Tables used:
  - `documents` — id, user_id, original_name, blob_url, anonymized_text, medical_entities (jsonb), pii_substitutions (jsonb), structured_result (jsonb), upload_date, file_blob_url
  - `health_entries` — id, user_id, entry_type, name, details, started_at, ended_at, active, created_at

**No ORM** — raw Supabase query builder (`.table().select().eq().execute()` pattern)

## External APIs

**Anthropic Claude (via Azure AI Foundry):**
- SDK: `anthropic` 0.28.0
- Client initialized in `backend/services/azure/llm.py` with custom `base_url` pointing to Azure AI Foundry endpoint
- Model used: `claude-sonnet-4-5` (both streaming and single-turn JSON extraction)
- Auth env vars: `ANTHROPIC_BASE_URL`, `ANTHROPIC_API_KEY` (also passed as `api-key` default header)
- Used for: RAG chat streaming (`chat_stream()`), structured JSON extraction from medical text (`generate_json()`)
- Mock mode: `USE_MOCK_AZURE=true` bypasses all API calls and returns hardcoded responses

**Azure Document Intelligence:**
- SDK: `azure-ai-formrecognizer` 3.3.3
- Client: `DocumentAnalysisClient` in `backend/services/azure/document_intelligence.py`
- Model: `prebuilt-read` for OCR
- Auth env vars: `DOCUMENT_INTELLIGENCE_ENDPOINT`, `DOCUMENT_INTELLIGENCE_KEY` (AzureKeyCredential)
- Used for: extracting raw text from uploaded PDF and image medical documents

**Azure Text Analytics for Health:**
- SDK: `azure-ai-textanalytics` 5.3.0
- Client: `TextAnalyticsClient` in `backend/services/azure/text_analytics.py`
- Operation: `begin_analyze_healthcare_entities()`
- Auth env vars: `TEXT_ANALYTICS_ENDPOINT`, `TEXT_ANALYTICS_KEY` (AzureKeyCredential)
- Used for: extracting clinical entities (diagnoses, medications, allergies, PII) from anonymized medical text

**Azure AI Search:**
- SDK: `azure-search-documents` 11.6.0b4 (beta)
- Client: `SearchClient` in `backend/services/azure/search.py`
- Index name: `uhr-health-records` (configurable via `SEARCH_INDEX_NAME`)
- Auth env vars: `SEARCH_ENDPOINT`, `SEARCH_KEY` (AzureKeyCredential)
- Strategy: single index with `user_id` field; all queries filter by `user_id eq '{user_id}'`
- Search type: keyword full-text (no vector embeddings)
- Used for: RAG retrieval — indexing anonymized document text, querying for relevant context per user query

**Azure Blob Storage:**
- SDK: `azure-storage-blob` 12.19.1
- Client: `BlobServiceClient.from_connection_string()` in `backend/services/azure/blob_storage.py`
- Auth env vars: `AZURE_STORAGE_CONNECTION_STRING`, `STORAGE_CONTAINER_NAME` (default: `health-records`)
- Blob naming: `{user_id}/{uuid}/{filename}`
- Used for: storing original uploaded medical document files; URLs stored in Supabase `documents.file_blob_url`

## Internal Services

**Backend API (FastAPI):**
- Base URL configured via `NEXT_PUBLIC_API_URL` in the frontend (default: `http://localhost:8000`)
- Frontend calls backend exclusively through `frontend/lib/api.ts` using `fetch()` with `Bearer` JWT auth header
- Auth header pattern: `Authorization: Bearer <supabase_access_token>` on all protected endpoints
- CORS: `http://localhost:3000` always allowed; `FRONTEND_URL` env var adds production origin

**Document Processing Pipeline:**
- Orchestrated in `backend/services/pipeline/orchestrator.py`
- Steps: extract text (Document Intelligence) → clean → classify → extract entities (Text Analytics) → anonymize → structure via Claude JSON call
- RAG indexing triggered post-upload in `backend/services/rag/indexer.py`

**Server-Sent Events (SSE) Chat Stream:**
- Endpoint: `POST /chat`
- Frontend reads SSE in `frontend/lib/api.ts` (`chatStream()`) using `ReadableStream` + `TextDecoder`
- Event types emitted: `sources`, `token`, `error`, `done`

**PDF / QR Generation (internal):**
- `backend/services/pdf_generator.py` — uses `reportlab` 4.1.0 to generate emergency PDF
- `backend/services/qr_generator.py` — uses `qrcode[pil]` 7.4.2 to generate QR codes
- No external service — generated server-side on request

## Authentication & Identity

**Provider:** Supabase Auth
- Frontend: `supabase.auth.getSession()` / `supabase.auth.signOut()` via `frontend/lib/supabase.ts`
- Route protection: client-side session checks (Next.js middleware at `frontend/middleware.ts` is inactive in static export mode)
- Public paths: `/login`, `/emergency/*` (no auth required)
- Backend validation: `backend/utils/auth.py` — calls `supabase.auth.get_user(token)` with service role key to validate Bearer JWT
- Dev bypass: `USE_MOCK_AZURE=true` causes backend to skip JWT validation and return `MOCK_USER_ID`

## Monitoring & Observability

**Azure Application Insights:**
- Configured in `backend/host.json` under `logging.applicationInsights` with sampling enabled
- Excludes `Request` type from sampling

**Error Logging:**
- Backend: standard Python exceptions surfaced as FastAPI `HTTPException` responses
- No dedicated error tracking SDK (e.g., Sentry) detected

## Deployment

**Frontend:**
- Platform: Azure Static Web Apps (free tier)
- Build: `next build` with `output: "export"` — produces static HTML/JS/CSS
- Routing: `frontend/staticwebapp.config.json` — SPA fallback to `/index.html`, security headers (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`)

**Backend:**
- Platform: Azure Functions v2 (Python)
- Entry point: `backend/function_app.py` — wraps FastAPI app via `AsgiMiddleware`
- Route: wildcard `{*route}` with anonymous HTTP auth level (JWT enforced inside FastAPI)
- Extension bundle: `Microsoft.Azure.Functions.ExtensionBundle` v4

## Environment Configuration

**Backend env vars** (defined in `backend/.env.example`):

| Variable | Purpose |
|---|---|
| `DOCUMENT_INTELLIGENCE_ENDPOINT` | Azure Document Intelligence service URL |
| `DOCUMENT_INTELLIGENCE_KEY` | Azure Document Intelligence API key |
| `TEXT_ANALYTICS_ENDPOINT` | Azure Text Analytics service URL |
| `TEXT_ANALYTICS_KEY` | Azure Text Analytics API key |
| `SEARCH_ENDPOINT` | Azure AI Search service URL |
| `SEARCH_KEY` | Azure AI Search admin key |
| `SEARCH_INDEX_NAME` | AI Search index name (default: `uhr-health-records`) |
| `AZURE_STORAGE_CONNECTION_STRING` | Blob Storage connection string |
| `STORAGE_CONTAINER_NAME` | Blob container name (default: `health-records`) |
| `ANTHROPIC_BASE_URL` | Azure AI Foundry Claude endpoint |
| `ANTHROPIC_API_KEY` | Anthropic/Azure AI Foundry API key |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_KEY` | Supabase anon/public key |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service role key (backend only) |
| `SUPABASE_JWT_SECRET` | Supabase JWT secret (present but auth uses `get_user()` instead) |
| `USE_MOCK_AZURE` | `"true"` skips all Azure/LLM calls — in-memory mocks used instead |
| `MOCK_USER_ID` | User ID returned when `USE_MOCK_AZURE=true` (default: `local-dev-user-001`) |
| `NEXT_PUBLIC_APP_URL` | Frontend URL (used in backend for CORS via `FRONTEND_URL`) |
| `FRONTEND_URL` | Production frontend origin added to CORS allowed list |

**Frontend env vars** (defined in `frontend/.env.local.example`):

| Variable | Purpose |
|---|---|
| `NEXT_PUBLIC_API_URL` | Backend API base URL (default: `http://localhost:8000`) |
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anon key (safe to expose in browser) |

**Secrets location:**
- `backend/.env` — present locally, not committed (in `.gitignore`)
- `frontend/.env.local` — present locally, not committed (in `.gitignore`)
- Production secrets managed via Azure Functions App Settings and Azure Static Web Apps environment variables

---

*Integration audit: 2026-04-02*
