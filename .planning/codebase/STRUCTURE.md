# Project Structure

## Directory Layout

```
uhr-ai/
├── backend/                          # FastAPI Python backend
│   ├── main.py                       # FastAPI app, CORS, router registration
│   ├── function_app.py               # Azure Functions entry point
│   ├── host.json                     # Azure Functions host config
│   ├── requirements.txt              # Python dependencies
│   ├── .env / .env.example           # Environment variables
│   ├── api/                          # Route handlers (thin controllers)
│   │   ├── upload.py                 # POST /upload
│   │   ├── documents.py              # GET /documents, GET /documents/{id}
│   │   ├── chat.py                   # POST /chat (SSE streaming)
│   │   ├── analysis.py               # POST /analysis
│   │   ├── emergency.py              # GET /emergency/{user_id} (no auth)
│   │   └── health_profile.py        # CRUD /health/*
│   ├── models/                       # Pydantic request/response schemas
│   │   ├── document.py               # Document, UploadResponse, StructuredResult
│   │   ├── chat.py                   # ChatRequest, ChatResponse
│   │   ├── analysis.py               # AnalysisRequest/Response
│   │   ├── emergency.py              # EmergencyProfile
│   │   └── health.py                 # HealthEntry schemas
│   ├── services/                     # Business logic
│   │   ├── pipeline/                 # Document processing pipeline
│   │   │   ├── orchestrator.py       # Main pipeline entry point
│   │   │   ├── classifier.py         # Document family classification
│   │   │   ├── cleaner.py            # Admin/clinical text separation
│   │   │   └── extractor.py          # LLM structured extraction
│   │   ├── azure/                    # Azure service wrappers
│   │   │   ├── blob_storage.py       # Azure Blob Storage upload
│   │   │   ├── document_intelligence.py  # OCR via Form Recognizer
│   │   │   ├── llm.py                # Claude (Anthropic) LLM calls
│   │   │   ├── search.py             # Azure AI Search CRUD
│   │   │   └── text_analytics.py     # Azure Text Analytics for Health (NER)
│   │   ├── rag/                      # Retrieval-Augmented Generation
│   │   │   ├── indexer.py            # Index documents after upload
│   │   │   └── retriever.py          # Retrieve chunks for chat
│   │   ├── anonymizer/               # PII anonymization (unused in upload flow)
│   │   │   └── pipeline.py
│   │   ├── document_store.py         # Supabase document persistence
│   │   ├── supabase_store.py         # Low-level Supabase client
│   │   ├── health_store.py           # Manual health entry persistence
│   │   ├── emergency.py              # Emergency profile aggregation
│   │   ├── pdf_generator.py          # PDF report generation
│   │   └── qr_generator.py           # QR code generation
│   ├── utils/
│   │   └── auth.py                   # JWT validation + mock bypass
│   └── scripts/
│       └── setup_azure_search.py     # One-time Azure Search index setup
│
├── frontend/                         # Next.js 14 frontend
│   ├── app/                          # App Router pages
│   │   ├── layout.tsx                # Root layout with nav
│   │   ├── page.tsx                  # Root redirect
│   │   ├── login/page.tsx            # Supabase auth login
│   │   ├── dashboard/page.tsx        # Patient summary dashboard
│   │   ├── upload/page.tsx           # Document upload + list
│   │   ├── chat/page.tsx             # AI chat interface
│   │   ├── saude/page.tsx            # Manual health entries
│   │   └── emergency/page.tsx        # Emergency profile view
│   ├── components/                   # Feature-organized React components
│   │   ├── auth/LogoutButton.tsx
│   │   ├── chat/ChatInterface.tsx
│   │   ├── dashboard/PatientSummary.tsx
│   │   ├── health/AddEntryForm.tsx
│   │   ├── health/HealthEntryList.tsx
│   │   └── upload/                   # Document upload components
│   ├── lib/                          # Utilities (API client, Supabase config)
│   ├── middleware.ts                  # Auth middleware (non-functional in static export)
│   ├── next.config.mjs               # output: "export" (static site)
│   ├── tailwind.config.ts
│   └── staticwebapp.config.json      # Azure Static Web Apps routing
│
└── .github/
    └── workflows/
        ├── deploy.yml                # Backend deploy workflow
        └── azure-static-web-apps-*.yml  # Frontend deploy workflow
```

## Entry Points

| Context | Entry Point |
|---|---|
| Local backend dev | `uvicorn main:app --reload` |
| Azure Functions (prod) | `function_app.py` |
| Frontend dev | `npm run dev` (Next.js dev server) |
| Frontend prod | `npm run build` → static export → Azure Static Web Apps |

## Module Organization
- **api/** = thin route handlers, only request parsing and response shaping
- **services/** = all business logic, grouped by domain (pipeline, azure, rag)
- **models/** = Pydantic schemas only, no logic
- **utils/** = cross-cutting concerns (auth)

## Key Files

| File | Purpose |
|---|---|
| `backend/.env.example` | Documents all required environment variables |
| `backend/services/pipeline/orchestrator.py` | Core document processing logic |
| `backend/main.py` | CORS config and router registration |
| `frontend/next.config.mjs` | Static export config (affects middleware behavior) |
| `frontend/staticwebapp.config.json` | Azure routing for SPA fallback |
