# Technology Stack

**Analysis Date:** 2026-04-02

## Languages

**Primary:**
- TypeScript 5.x - Frontend (Next.js app, all `.ts`/`.tsx` files under `frontend/`)
- Python 3.x - Backend (FastAPI app, all `.py` files under `backend/`)

**Secondary:**
- CSS (via Tailwind utility classes only — no raw CSS files)

## Runtime

**Frontend:**
- Node.js (version governed by `frontend/package-lock.json`, Next.js 14 requires Node 18+)

**Backend:**
- Python 3.x (exact version not pinned in a `.python-version` file; runtime assumed from Azure Functions v2 host)
- Azure Functions host v4 (`backend/host.json` — extension bundle `[4.*, 5.0.0)`)
- Local dev server: `uvicorn main:app --reload` (port 8000)

## Package Manager

**Frontend:**
- npm — lockfile present at `frontend/package-lock.json`

**Backend:**
- pip — `backend/requirements.txt`

## Frameworks

**Core (Frontend):**
- Next.js 14.2.35 - React framework, configured for static export (`output: "export"` in `frontend/next.config.mjs`)
- React 18.x - UI rendering

**Core (Backend):**
- FastAPI 0.111.0 - REST API framework (`backend/main.py`)
- Uvicorn 0.29.0 (standard extras) - ASGI server for local development
- Azure Functions 1.21.3 - Serverless deployment wrapper (`backend/function_app.py`, wraps FastAPI via `AsgiMiddleware`)
- Pydantic 2.7.1 - Request/response schema validation
- pydantic-settings 2.2.1 - Settings management via environment variables

**UI / Component Library:**
- Tailwind CSS 3.4.1 - Utility-first CSS framework (`frontend/tailwind.config.ts`, `frontend/postcss.config.mjs`)
- Radix UI — headless component primitives:
  - `@radix-ui/react-dialog` ^1.1.15
  - `@radix-ui/react-slot` ^1.2.4
- class-variance-authority 0.7.1 - CVA for typed component variants
- clsx 2.1.1 - Conditional className utility
- tailwind-merge 3.5.0 - Merge Tailwind classes without conflicts
- lucide-react 1.7.0 - Icon library

**Testing (Backend):**
- pytest 8.2.0
- pytest-asyncio 0.23.7
- httpx 0.27.0 - Async HTTP client for tests

## Build & Dev Tools

**Frontend:**
- `next build` → produces static export in `frontend/out/` (due to `output: "export"`)
- `next dev` → local development server (port 3000)
- `next lint` → ESLint via `frontend/.eslintrc.json`
- postcss 8.x (Tailwind processing)

**Backend:**
- `uvicorn main:app --reload` → local dev
- Azure Functions Core Tools for function host emulation
- `python-dotenv 1.0.1` → loads `backend/.env` for local dev

## Dev Tools

**Linting (Frontend):**
- ESLint 8.x with `eslint-config-next` 14.2.35 — config at `frontend/.eslintrc.json`

**Type Checking (Frontend):**
- TypeScript 5.x in strict mode (`"strict": true` in `frontend/tsconfig.json`)
- Path alias: `@/*` maps to `frontend/*`
- Module resolution: `"bundler"` mode

**Formatting:**
- No Prettier or Biome config file detected — not enforced

## Key Dependencies Summary

| Package | Version | Layer | Purpose |
|---|---|---|---|
| `next` | 14.2.35 | Frontend | React framework + routing |
| `@supabase/ssr` | ^0.9.0 | Frontend | Supabase SSR client (browser + server) |
| `@supabase/supabase-js` | ^2.100.1 | Frontend | Supabase JS client |
| `fastapi` | 0.111.0 | Backend | REST API |
| `anthropic` | 0.28.0 | Backend | Claude LLM SDK |
| `supabase` | 2.4.6 | Backend | Supabase Python client |
| `azure-ai-formrecognizer` | 3.3.3 | Backend | Document Intelligence OCR |
| `azure-ai-textanalytics` | 5.3.0 | Backend | Health entity extraction |
| `azure-search-documents` | 11.6.0b4 | Backend | AI Search (RAG) |
| `azure-storage-blob` | 12.19.1 | Backend | Blob Storage for files |
| `azure-functions` | 1.21.3 | Backend | Serverless hosting wrapper |
| `reportlab` | 4.1.0 | Backend | PDF generation |
| `qrcode[pil]` | 7.4.2 | Backend | QR code generation |
| `PyJWT` | 2.8.0 | Backend | JWT handling (imported but auth now uses Supabase client) |
| `cryptography` | 42.0.5 | Backend | JWT/crypto support |
| `python-multipart` | 0.0.9 | Backend | File upload form parsing |

---

*Stack analysis: 2026-04-02*
