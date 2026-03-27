from pydantic import BaseModel


class SuggestedSpecialty(BaseModel):
    specialty: str
    reason: str


class AnalysisResult(BaseModel):
    user_id: str
    case_summary: str
    diagnoses: list[str]
    active_medications: list[str]
    allergies: list[str]
    suggested_specialties: list[SuggestedSpecialty]
    document_count: int
    disclaimer: str = (
        "As hipóteses e sugestões abaixo são geradas por IA com base nos documentos "
        "fornecidos e não constituem diagnóstico médico. Consulte um profissional de saúde habilitado."
    )
