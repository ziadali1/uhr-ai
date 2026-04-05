---
phase: 01-adaptive-text-extraction
plan: 4
type: execute
wave: 4
depends_on:
  - 01-PLAN-3-adaptive-router
files_modified:
  - backend/models/document.py
  - backend/services/supabase_store.py
  - backend/services/document_store.py
  - backend/api/upload.py
  - backend/tests/extraction/test_metadata_storage.py
autonomous: true
requirements:
  - INGEST-05

must_haves:
  truths:
    - "After upload, the documents table row has a non-null text_extraction_meta JSONB column"
    - "text_extraction_meta contains method, quality_score, page_strategies, library, fallback_reason, extracted_at"
    - "The mock store saves text_extraction_meta in the in-memory DocumentDetail object"
    - "The Supabase store writes text_extraction_meta in the INSERT row dict"
    - "upload.py calls extract_text_with_meta() instead of extract_text() and passes the metadata forward"
  artifacts:
    - path: "backend/models/document.py"
      provides: "ExtractionMeta Pydantic model and text_extraction_meta field on DocumentDetail"
      contains: "ExtractionMeta"
    - path: "backend/services/supabase_store.py"
      provides: "Writes text_extraction_meta in save() INSERT"
      contains: "text_extraction_meta"
    - path: "backend/services/document_store.py"
      provides: "Mock store propagates text_extraction_meta from DocumentDetail"
    - path: "backend/api/upload.py"
      provides: "Calls extract_text_with_meta() and stores ExtractionMeta"
      contains: "extract_text_with_meta"
    - path: "backend/tests/extraction/test_metadata_storage.py"
      provides: "Tests for meta model and store persistence"
  key_links:
    - from: "backend/api/upload.py"
      to: "backend/services/azure/document_intelligence.py"
      via: "from services.azure.document_intelligence import extract_text_with_meta"
      pattern: "extract_text_with_meta"
    - from: "backend/services/supabase_store.py"
      to: "backend/models/document.py"
      via: "detail.text_extraction_meta.model_dump()"
      pattern: "text_extraction_meta"
---

<objective>
Add `text_extraction_meta` JSONB storage — the Supabase column, the Pydantic model, and the upload wiring that persists metadata on every document.

Purpose: Every extraction now generates structured metadata (method, quality_score, library, etc.). This plan ensures that metadata is stored so it can be queried, monitored, and used in Plan 5's edge-case handling.
Output: `ExtractionMeta` model, updated `DocumentDetail`, updated `supabase_store.save()`, updated `upload.py`.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/research/extraction.md
@backend/models/document.py
@backend/services/supabase_store.py
@backend/services/document_store.py
</context>

<interfaces>
<!-- Contracts this plan builds on. -->

From Plan 3 — document_intelligence.py:
```python
def extract_text_with_meta(file_bytes: bytes, filename: str) -> dict:
    """
    Returns dict with keys:
      text            (str)
      method          (str)   "native" | "ocr"
      quality_score   (float)
      fallback_reason (str | None)
      page_strategies (list[dict])
      library         (str)
    """
```

Current DocumentDetail (models/document.py lines 128-136):
```python
class DocumentDetail(BaseModel):
    document_id: str
    user_id: str
    original_name: str
    upload_date: datetime
    anonymized_text: str
    medical_entities: list[ExtractedEntity]
    pii_substitutions: list[str]
    structured_result: StructuredResult | None = None
    file_blob_url: str | None = None
```

Current supabase_store.save() INSERT dict (lines 29-42):
```python
row: dict = {
    "id": detail.document_id,
    "user_id": detail.user_id,
    "original_name": detail.original_name,
    "blob_url": "",
    "anonymized_text": detail.anonymized_text,
    "medical_entities": [...],
    "pii_substitutions": detail.pii_substitutions,
    "upload_date": detail.upload_date.isoformat(),
    "file_blob_url": detail.file_blob_url,
}
if detail.structured_result is not None:
    row["structured_result"] = detail.structured_result.model_dump()
```
</interfaces>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add ExtractionMeta model and text_extraction_meta field to DocumentDetail</name>
  <read_first>
    backend/models/document.py
    .planning/research/extraction.md
  </read_first>
  <files>
    backend/models/document.py
    backend/tests/extraction/test_metadata_storage.py
  </files>
  <behavior>
    - ExtractionMeta is a Pydantic BaseModel with fields:
        method (str): "native" | "ocr"
        quality_score (float): [0.0, 1.0]
        page_strategies (list[dict]): per-page results (default [])
        library (str): version string
        fallback_reason (str | None): default None
        extracted_at (str): ISO 8601 datetime string
    - ExtractionMeta.model_dump() produces a JSON-serializable dict (no datetime objects)
    - DocumentDetail has a new optional field: text_extraction_meta (ExtractionMeta | None = None)
    - All existing DocumentDetail fields and their defaults are preserved
    - Test: ExtractionMeta can be constructed from the dict returned by extract_text_with_meta() plus an extracted_at timestamp
    - Test: DocumentDetail with text_extraction_meta=None still passes model validation
    - Test: DocumentDetail with a populated ExtractionMeta validates correctly
  </behavior>
  <action>
    Open `backend/models/document.py`. Add after the imports block but before `class ExtractedEntity`:

    ```python
    class ExtractionMeta(BaseModel):
        """
        Metadata about how text was extracted from a document.
        Stored as JSONB in documents.text_extraction_meta.

        Fields match the dict returned by extract_text_with_meta() in document_intelligence.py.
        """
        method: str                        # "native" | "ocr"
        quality_score: float               # [0.0, 1.0]
        page_strategies: list[dict] = []   # per-page is_native_page() results
        library: str                       # e.g. "pymupdf/1.24.5" or "azure-ai-formrecognizer/3.3.3"
        fallback_reason: str | None = None # why native was rejected, or None
        extracted_at: str                  # ISO 8601 datetime string
    ```

    Then in the `DocumentDetail` class (at the bottom of the file), add one new optional field as the last field:

    ```python
        text_extraction_meta: ExtractionMeta | None = None
    ```

    The final DocumentDetail class must look like:
    ```python
    class DocumentDetail(BaseModel):
        document_id: str
        user_id: str
        original_name: str
        upload_date: datetime
        anonymized_text: str
        medical_entities: list[ExtractedEntity]
        pii_substitutions: list[str]
        structured_result: StructuredResult | None = None
        file_blob_url: str | None = None
        text_extraction_meta: ExtractionMeta | None = None
    ```

    Create `backend/tests/extraction/test_metadata_storage.py`:

    ```python
    """Tests for ExtractionMeta model and DocumentDetail integration."""
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

    from datetime import datetime, timezone
    import pytest
    from models.document import ExtractionMeta, DocumentDetail, ExtractedEntity


    def _make_meta(**overrides):
        defaults = {
            "method": "native",
            "quality_score": 0.82,
            "page_strategies": [{"is_native": True, "char_count": 200}],
            "library": "pymupdf/1.24.5",
            "fallback_reason": None,
            "extracted_at": datetime.now(timezone.utc).isoformat(),
        }
        defaults.update(overrides)
        return ExtractionMeta(**defaults)


    def test_extraction_meta_construction():
        meta = _make_meta()
        assert meta.method == "native"
        assert 0.0 <= meta.quality_score <= 1.0
        assert meta.fallback_reason is None


    def test_extraction_meta_ocr_fallback():
        meta = _make_meta(method="ocr", fallback_reason="low_quality", quality_score=0.40)
        assert meta.method == "ocr"
        assert meta.fallback_reason == "low_quality"


    def test_extraction_meta_model_dump_is_serializable():
        import json
        meta = _make_meta()
        dumped = meta.model_dump()
        # Must not raise
        serialized = json.dumps(dumped)
        assert "native" in serialized


    def test_document_detail_without_meta_is_valid():
        detail = DocumentDetail(
            document_id="doc-1",
            user_id="user-1",
            original_name="test.pdf",
            upload_date=datetime.now(timezone.utc),
            anonymized_text="Some text",
            medical_entities=[],
            pii_substitutions=[],
        )
        assert detail.text_extraction_meta is None


    def test_document_detail_with_meta_is_valid():
        meta = _make_meta()
        detail = DocumentDetail(
            document_id="doc-1",
            user_id="user-1",
            original_name="test.pdf",
            upload_date=datetime.now(timezone.utc),
            anonymized_text="Some text",
            medical_entities=[],
            pii_substitutions=[],
            text_extraction_meta=meta,
        )
        assert detail.text_extraction_meta is not None
        assert detail.text_extraction_meta.method == "native"


    def test_extraction_meta_from_router_output():
        """Simulate constructing ExtractionMeta from extract_text_with_meta() dict."""
        router_output = {
            "text": "Texto extraído",
            "method": "native",
            "quality_score": 0.88,
            "fallback_reason": None,
            "page_strategies": [{"is_native": True}],
            "library": "pymupdf/1.24.5",
        }
        meta = ExtractionMeta(
            method=router_output["method"],
            quality_score=router_output["quality_score"],
            page_strategies=router_output["page_strategies"],
            library=router_output["library"],
            fallback_reason=router_output["fallback_reason"],
            extracted_at=datetime.now(timezone.utc).isoformat(),
        )
        assert meta.method == "native"
        assert meta.quality_score == 0.88
    ```
  </action>
  <verify>
    <automated>cd backend && python -m pytest tests/extraction/test_metadata_storage.py -v 2>&1</automated>
  </verify>
  <done>All 6 tests pass. `ExtractionMeta` is importable from `models.document`. `DocumentDetail` has `text_extraction_meta` field.</done>
</task>

<task type="auto">
  <name>Task 2: Persist text_extraction_meta in Supabase store and wire upload.py</name>
  <read_first>
    backend/services/supabase_store.py
    backend/services/document_store.py
    backend/api/upload.py
    backend/models/document.py
  </read_first>
  <files>
    backend/services/supabase_store.py
    backend/api/upload.py
  </files>
  <action>
    **Part A — supabase_store.py:**

    Open `backend/services/supabase_store.py`. In the `save()` function, after the block that handles `structured_result`, add:

    ```python
        if detail.text_extraction_meta is not None:
            row["text_extraction_meta"] = detail.text_extraction_meta.model_dump()
    ```

    Also update `_row_to_detail()` to hydrate the field when reading back from Supabase.
    Add to the `_row_to_detail()` function, before the `return DocumentDetail(...)` call:

    ```python
        text_extraction_meta = None
        if row.get("text_extraction_meta"):
            try:
                from models.document import ExtractionMeta
                text_extraction_meta = ExtractionMeta(**row["text_extraction_meta"])
            except Exception:
                pass
    ```

    And pass it in the `DocumentDetail(...)` constructor:
    ```python
        text_extraction_meta=text_extraction_meta,
    ```

    NOTE: The Supabase `documents` table does NOT yet have the `text_extraction_meta` column in production.
    The INSERT will silently fail on that column until a migration adds it.
    Add a comment in the code: `# Column added in Phase 1 migration — see .planning/phases/01-adaptive-text-extraction/`
    The column will be added via the Supabase dashboard or a migration script.
    For now, wrap only the text_extraction_meta INSERT in a try/except so missing column does not break existing uploads:

    ```python
        try:
            if detail.text_extraction_meta is not None:
                row["text_extraction_meta"] = detail.text_extraction_meta.model_dump()
        except Exception:
            pass  # column may not exist yet; migration required
    ```

    **Part B — upload.py:**

    Read `backend/api/upload.py`. Find the line that calls `extract_text(...)` or imports from `document_intelligence`. Replace:

    ```python
    from services.azure.document_intelligence import extract_text
    # and later:
    raw_text = extract_text(file_bytes, filename)
    ```

    with:

    ```python
    from services.azure.document_intelligence import extract_text_with_meta
    from models.document import ExtractionMeta
    from datetime import datetime, timezone
    # and later:
    extraction_result = extract_text_with_meta(file_bytes, filename)
    raw_text = extraction_result["text"]
    extraction_meta = ExtractionMeta(
        method=extraction_result["method"],
        quality_score=extraction_result["quality_score"],
        page_strategies=extraction_result["page_strategies"],
        library=extraction_result["library"],
        fallback_reason=extraction_result["fallback_reason"],
        extracted_at=datetime.now(timezone.utc).isoformat(),
    )
    ```

    Then, when constructing `DocumentDetail` in upload.py, pass `text_extraction_meta=extraction_meta`.

    If upload.py does not currently construct `DocumentDetail` directly (it may delegate to pipeline/orchestrator and then call document_store.save), locate where `DocumentDetail` is instantiated or where the store's `save()` is called, and thread `extraction_meta` through appropriately.

    IMPORTANT: Do not change the HTTP response schema of `POST /upload`. `UploadResponse` is unchanged.
  </action>
  <verify>
    <automated>cd backend && python -c "from services.supabase_store import save; from services.azure.document_intelligence import extract_text_with_meta; print('ok')"</automated>
  </verify>
  <done>
    - `supabase_store.py` contains `text_extraction_meta` in the INSERT row dict
    - `supabase_store.py` contains `_row_to_detail` hydration for `text_extraction_meta`
    - `upload.py` imports `extract_text_with_meta` (grep confirms)
    - `upload.py` constructs `ExtractionMeta` and passes it to `DocumentDetail`
    - `cd backend && python -c "from api.upload import router; print('ok')"` prints "ok"
  </done>
</task>

</tasks>

<verification>
- `cd backend && python -m pytest tests/extraction/test_metadata_storage.py -v` exits 0 with 6 passed
- `grep -n "text_extraction_meta" backend/services/supabase_store.py` shows lines in both save() and _row_to_detail()
- `grep -n "extract_text_with_meta" backend/api/upload.py` shows import and usage
- `grep -n "ExtractionMeta" backend/models/document.py` shows class definition
- `cd backend && python -c "from models.document import ExtractionMeta, DocumentDetail; print('ok')"` prints "ok"
</verification>

<success_criteria>
- `ExtractionMeta` Pydantic model captures all metadata fields from the router output dict
- `DocumentDetail.text_extraction_meta` is optional for backward compatibility
- `supabase_store.save()` writes `text_extraction_meta` JSONB when present
- `upload.py` calls `extract_text_with_meta()` and constructs `ExtractionMeta` for every upload
- No changes to the HTTP response shape of `POST /upload`
</success_criteria>

<output>
After completion, create `.planning/phases/01-adaptive-text-extraction/01-4-SUMMARY.md`

Also note in the summary: a Supabase migration must be run to add the `text_extraction_meta JSONB` column to the `documents` table. SQL: `ALTER TABLE documents ADD COLUMN IF NOT EXISTS text_extraction_meta JSONB;`
</output>
