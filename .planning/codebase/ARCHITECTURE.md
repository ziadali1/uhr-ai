# Architecture

## System Overview
UHR (Unified Health Record) is a personal medical document centralizer and AI assistant. Users upload medical documents (PDFs/images), the system extracts structured clinical data via an AI pipeline, stores it, and provides a chat interface to query their health history.

## Architecture Pattern
**Monorepo with two-tier separation:**
- **Backend:** FastAPI (Python) — REST + SSE API deployed as Azure Functions or standalone uvicorn
- **Frontend:** Next.js 14 (TypeScript, App Router) — static export deployed to Azure Static Web Apps

The frontend calls the backend API directly; there is no BFF layer.

## Data Flow

```
User uploads PDF/image
  → POST /upload
  → Azure Blob Storage (original file)
  → Pipeline orchestrator:
      1. Azure Document Intelligence (OCR → raw_text)
      2. Classifier (rule-based → document_family)
      3. Cleaner (separate admin vs clinical text)
      4. Extractor (Claude LLM → StructuredResult)
      5. Entity builder (from structured data)
  → Azure AI Search (RAG index)
  → Supabase (document record + structured data)

User sends chat message
  → POST /chat (SSE stream)
  → Azure AI Search retrieval (top_k=3 chunks)
  → Claude LLM (Anthropic) → streaming response

Emergency QR code scan
  → GET /emergency/{user_id}  ← NO AUTH
  → Supabase health profile query
  → Returns medications, allergies, complaints
```

## Key Components

| Component | Location | Role |
|---|---|---|
| Pipeline orchestrator | `backend/services/pipeline/orchestrator.py` | Coordinates the full OCR→classify→clean→extract flow |
| Classifier | `backend/services/pipeline/classifier.py` | Rule-based document family detection |
| Extractor | `backend/services/pipeline/extractor.py` | LLM-based structured data extraction |
| RAG indexer | `backend/services/rag/indexer.py` | Indexes documents in Azure AI Search |
| RAG retriever | `backend/services/rag/retriever.py` | Retrieves relevant chunks for chat |
| Document store | `backend/services/document_store.py` | Supabase persistence layer |
| Health store | `backend/services/health_store.py` | Manual health entries (meds, allergies, complaints) |
| Auth util | `backend/utils/auth.py` | JWT validation via Supabase (mock-able) |

## Document Families
The system classifies documents into 4 families:
- `structured_lab` — blood/lab results
- `imaging_narrative` — X-ray, MRI, CT reports
- `clinical_narrative` — consultation notes, discharge summaries
- `medication_document` — prescriptions
- `unknown` — fallback to Azure Text Analytics NER

## State Management
- **Backend:** Stateless; all state in Supabase (DB) and Azure AI Search (vector index)
- **Frontend:** React local state per page; no global state manager (no Redux/Zustand)
- **Mock mode:** `USE_MOCK_AZURE=true` enables in-memory stores (lost on restart)
