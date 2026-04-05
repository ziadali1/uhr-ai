"""
Azure Document Intelligence — OCR de PDFs e imagens de laudos médicos.
Com USE_MOCK_AZURE=true, retorna texto de exemplo sem Azure real.

v2: extract_text() now delegates to the adaptive router in services/extraction/router.py.
Native-text PDFs are extracted via PyMuPDF when quality score >= 0.65.
OCR (Azure Document Intelligence) is used as fallback.

The public interface is unchanged: extract_text(file_bytes, filename) -> str.
Callers that need extraction metadata should call extract_text_with_meta() instead.
"""
import os
from io import BytesIO


def _use_mock() -> bool:
    return os.getenv("USE_MOCK_AZURE", "true").lower() == "true"


_MOCK_TEXT = """
LAUDO MÉDICO
Paciente: João Silva
CPF: 123.456.789-00
Data de nascimento: 15/03/1965
CRM médico: 12345-SP

Diagnóstico: Diabetes mellitus tipo 2 (CID E11)
Fibrilação atrial paroxística (CID I48)

Medicamentos em uso:
- Metformina 850mg - 2x ao dia
- Warfarina 5mg - 1x ao dia (INR alvo 2,0-3,0)

Alergias conhecidas:
- Dipirona (reação anafilática severa)
- Penicilina (urticária)

Tipo sanguíneo: A positivo

Observações: Paciente com risco cirúrgico elevado devido ao uso de anticoagulante.
Necessário avaliar suspensão da Warfarina 5 dias antes de qualquer procedimento.

Dr. Maria Souza - CRM 54321-SP
Data: 15/03/2024
"""


def _extract_text_ocr(file_bytes: bytes, filename: str) -> str:
    """
    Call Azure Document Intelligence (prebuilt-read) to OCR a document.
    This is the raw OCR implementation used as fallback by the adaptive router.
    """
    if _use_mock():
        return _MOCK_TEXT.strip()

    from azure.ai.formrecognizer import DocumentAnalysisClient
    from azure.core.credentials import AzureKeyCredential

    endpoint = os.environ["DOCUMENT_INTELLIGENCE_ENDPOINT"]
    key = os.environ["DOCUMENT_INTELLIGENCE_KEY"]

    client = DocumentAnalysisClient(endpoint, AzureKeyCredential(key))
    poller = client.begin_analyze_document(
        "prebuilt-read",
        document=BytesIO(file_bytes),
    )
    result = poller.result()

    lines = []
    for page in result.pages:
        for line in (page.lines or []):
            lines.append(line.content)

    return "\n".join(lines)


def extract_text_with_meta(file_bytes: bytes, filename: str) -> dict:
    """
    Adaptive extraction with full metadata.

    Returns dict with keys:
      text            (str)
      method          (str)   "native" | "ocr"
      quality_score   (float)
      fallback_reason (str | None)
      page_strategies (list[dict])
      library         (str)

    Use this function when you need to persist text_extraction_meta.
    """
    if _use_mock():
        return {
            "text": _MOCK_TEXT.strip(),
            "method": "ocr",
            "quality_score": 0.85,
            "fallback_reason": None,
            "page_strategies": [],
            "library": "mock",
        }

    from services.extraction.router import extract_text_adaptive
    return extract_text_adaptive(file_bytes, filename, _extract_text_ocr)


def extract_text(file_bytes: bytes, filename: str) -> str:
    """
    Extract text from a PDF or image.

    Drop-in replacement for the original OCR-only implementation.
    Now routes through the adaptive extractor (native PyMuPDF when quality >= 0.65,
    OCR fallback otherwise).

    Returns the extracted text string. For full extraction metadata, use
    extract_text_with_meta() instead.
    """
    return extract_text_with_meta(file_bytes, filename)["text"]
