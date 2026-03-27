"""
Azure Document Intelligence — OCR de PDFs e imagens de laudos médicos.
Com USE_MOCK_AZURE=true, retorna texto de exemplo sem Azure real.
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


def extract_text(file_bytes: bytes, filename: str) -> str:
    """
    Extrai texto de um PDF ou imagem usando Azure Document Intelligence.
    Retorna o texto completo extraído.
    """
    if _use_mock():
        return _MOCK_TEXT.strip()

    from azure.ai.documentintelligence import DocumentIntelligenceClient
    from azure.core.credentials import AzureKeyCredential

    endpoint = os.environ["DOCUMENT_INTELLIGENCE_ENDPOINT"]
    key = os.environ["DOCUMENT_INTELLIGENCE_KEY"]

    client = DocumentIntelligenceClient(endpoint, AzureKeyCredential(key))

    poller = client.begin_analyze_document(
        "prebuilt-read",
        analyze_request=BytesIO(file_bytes),
        content_type="application/octet-stream",
    )
    result = poller.result()

    lines = []
    for page in result.pages:
        for line in (page.lines or []):
            lines.append(line.content)

    return "\n".join(lines)
