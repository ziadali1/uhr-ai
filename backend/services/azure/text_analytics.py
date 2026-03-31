"""
Azure Text Analytics for Health — extração de entidades médicas e PII.
Com USE_MOCK_AZURE=true, retorna entidades de exemplo sem Azure real.
"""
import os
from models.document import ExtractedEntity


def _use_mock() -> bool:
    return os.getenv("USE_MOCK_AZURE", "true").lower() == "true"


_MOCK_ENTITIES = [
    ExtractedEntity(text="João Silva", category="PersonName", confidence=0.99),
    ExtractedEntity(text="123.456.789-00", category="PersonId", confidence=0.99),
    ExtractedEntity(text="12345-SP", category="MedicalRegistration", confidence=0.97),
    ExtractedEntity(text="Dr. Maria Souza", category="PersonName", confidence=0.98),
    ExtractedEntity(text="54321-SP", category="MedicalRegistration", confidence=0.97),
    ExtractedEntity(text="Diabetes mellitus tipo 2", category="Diagnosis",
                    normalized_text="Type 2 diabetes mellitus", confidence=0.99),
    ExtractedEntity(text="Fibrilação atrial paroxística", category="Diagnosis",
                    normalized_text="Paroxysmal atrial fibrillation", confidence=0.98),
    ExtractedEntity(text="Metformina 850mg", category="MedicationName",
                    normalized_text="Metformin", confidence=0.99),
    ExtractedEntity(text="Warfarina 5mg", category="MedicationName",
                    normalized_text="Warfarin", confidence=0.99),
    ExtractedEntity(text="Dipirona", category="AllergyEntity",
                    normalized_text="Metamizole", confidence=0.97),
    ExtractedEntity(text="Penicilina", category="AllergyEntity",
                    normalized_text="Penicillin", confidence=0.98),
]

# Categorias com relevância clínica real — exclui números, datas, abreviações
CLINICAL_CATEGORIES = {
    "Diagnosis", "MedicationName", "Dosage", "AllergyEntity",
    "SymptomOrSign", "BodyStructure", "TreatmentName",
    "ExaminationName", "MedicalCondition", "Frequency",
    "MedicationRoute", "HealthcareProfession", "Age", "Gender",
}

MIN_CONFIDENCE = 0.80
MIN_TEXT_LENGTH = 5

# Termos de cabeçalho/contexto laboratorial que não são entidades clínicas
_BLOCKLIST = {
    "cpf", "crm", "crf", "cnes", "rg", "cnpj",
    "homens", "mulheres", "grávidas", "adultos", "crianças",
    "soro", "plasma", "sangue total", "edta",
    "conveni", "sanitária", "sani tária",
    "dia", "data", "req", "paginas", "página",
    "laboratorio", "laboratório", "unidade", "matriz", "registro",
}


def extract_health_entities(text: str) -> list[ExtractedEntity]:
    """
    Extrai entidades médicas e PII usando Text Analytics for Health.
    Retorna lista de entidades identificadas.
    """
    if _use_mock():
        return _MOCK_ENTITIES

    from azure.ai.textanalytics import TextAnalyticsClient
    from azure.core.credentials import AzureKeyCredential

    endpoint = os.environ["TEXT_ANALYTICS_ENDPOINT"]
    key = os.environ["TEXT_ANALYTICS_KEY"]

    client = TextAnalyticsClient(endpoint, AzureKeyCredential(key))
    poller = client.begin_analyze_healthcare_entities([text])
    results = poller.result()

    entities: list[ExtractedEntity] = []
    for doc in results:
        if doc.is_error:
            continue
        for entity in doc.entities:
            category = str(entity.category)
            text_clean = entity.text.strip()
            if (
                category not in CLINICAL_CATEGORIES
                or entity.confidence_score < MIN_CONFIDENCE
                or len(text_clean) < MIN_TEXT_LENGTH
                or text_clean.lower() in _BLOCKLIST
            ):
                continue
            entities.append(ExtractedEntity(
                text=entity.text,
                category=category,
                normalized_text=entity.normalized_text,
                confidence=entity.confidence_score,
            ))
    return entities
