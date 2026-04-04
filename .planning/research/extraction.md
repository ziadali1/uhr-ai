# Research: Adaptive PDF Text Extraction

## Key Finding

The change is surgical — everything is isolated to `services/azure/document_intelligence.py`. The orchestrator, classifier, cleaner, and LLM extractor are all untouched.

## Library Recommendation: PyMuPDF (`pymupdf`)

Install as `pip install pymupdf` (not `fitz` — that's an unrelated unmaintained package).

**License:** AGPL-3.0. For closed-source SaaS, needs legal sign-off. `pdfplumber` (MIT) is the safe fallback at modest performance cost.

**PyMuPDF wins because:**
- Fastest of the three options
- Exposes per-character font metadata needed for quality scoring
- Handles Portuguese diacritics, ICP-Brasil digitally-signed PDFs, and rotated pages without special handling

## Detection Logic

Per-page, three signals in order of reliability:

1. **Character count** — `len(page.get_text("text").strip())`. Threshold: <50 chars = not native.
2. **Image coverage ratio** — area of embedded raster images / page area. Threshold: >60% = image-dominant.
3. **Font sanity** — reject pages whose only fonts are `GlyphLessFont` or size-0 invisible OCR artifacts (produced by Acrobat's background OCR on scanned PDFs).

**Composite:** page is "native" if `char_count ≥ 50 AND image_coverage < 60% AND has real fonts`.

## Quality Scoring

Four signals combined into a [0,1] score:

| Signal | Weight | What it catches |
|--------|--------|-----------------|
| Printable character ratio | 0.40 | Corrupt font encodings |
| Word-like token density | 0.35 | Garbage encoding |
| Average line length normalized to 60 chars | 0.15 | Invisible-text artifacts |
| Numeric density normalized to 15% | 0.10 | Confirms medical document structure |

**Threshold: 0.65** to use native extraction over OCR. Starting point — calibrate after processing 50+ real documents. Good PDFs should cluster at 0.80+.

## Routing Pattern

```
if not PDF → OCR
if all pages native → native extraction → score → if ≥0.65 use it, else OCR
if all pages scanned → OCR
if mixed pages → OCR (v1 safe fallback; v2 can do page-level routing)
```

## Storage: One New JSONB Column

Add `text_extraction_meta JSONB` to the `documents` table. Fields:
- `method`: `native | ocr | hybrid_ocr`
- `quality_score`: float [0,1]
- `page_strategies`: array of per-page decisions
- `library`: version string
- `fallback_reason`: why native was rejected (if applicable)
- `extracted_at`: timestamp

**Do not store two full text copies** — the original PDF is already in Blob Storage and can be re-extracted if scoring logic improves.

## Medical PDF Pitfalls

1. **Embedded images in text-layer PDFs** — handled by per-page classification (logos/barcodes have small image coverage)
2. **AcroForm field values** — PyMuPDF's `page.widgets()` needed to collect filled form field values; relevant for MEMED/iClinic digital prescriptions
3. **ICP-Brasil signed PDFs** — PyMuPDF opens them correctly; no special handling needed
4. **Password-protected PDFs** — attempt `doc.authenticate("")` first (print-protection-only is common), then raise 422 rather than silently routing to OCR
5. **Truncated/corrupt PDFs** — PyMuPDF attempts self-repair; wrap all opens in try/except and fall back to OCR
6. **QR codes on native pages** — inflate char count; guard with `avg_line_length()` (QR URL = one very long line, genuine content = many short lines)

## Implementation Sketch

```python
import fitz  # pymupdf

def extract_text_adaptive(file_bytes: bytes, filename: str) -> dict:
    if not filename.lower().endswith(".pdf"):
        return {"method": "ocr", "text": extract_text_ocr(file_bytes, filename)}
    
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    page_results = [classify_page(p) for p in doc]
    
    all_native = all(r["is_native"] for r in page_results)
    if all_native:
        text = "\n".join(r["text"] for r in page_results)
        score = compute_quality_score(text)
        if score >= 0.65:
            return {"method": "native", "text": text, "quality_score": score, ...}
    
    # fallback
    ocr_text = extract_text_ocr(file_bytes, filename)
    return {"method": "ocr", "text": ocr_text, "quality_score": compute_quality_score(ocr_text), ...}
```
