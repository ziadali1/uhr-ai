"""
GET /analysis/{user_id} — analisa o histórico completo do paciente.

Agrega entidades de todos os documentos, gera resumo do caso,
hipóteses diagnósticas e sugestões de especialidades via LLM (ou mock).
"""
from fastapi import APIRouter, Depends, HTTPException

from models.analysis import AnalysisResult
from services.analysis import analyze_patient
from utils.auth import get_current_user

router = APIRouter()


@router.get("/analysis", response_model=AnalysisResult)
def get_analysis(user_id: str = Depends(get_current_user)):
    result = analyze_patient(user_id)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Nenhum documento encontrado. Faça upload de documentos médicos primeiro.",
        )
    return result
