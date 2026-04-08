"""
Patient Summary API — aggregated clinical summary endpoint.

Exposes the patient query service (Plan 01) via REST per D-03/D-07.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from utils.auth import get_current_user
from services.patient_query import get_patient_summary

router = APIRouter()


class LatestLabItem(BaseModel):
    analyte_norm: str
    analyte_raw: str | None
    value_str: str | None
    value_num: float | None
    unit: str | None
    ref_low: float | None
    ref_high: float | None
    flag: str | None
    needs_review: bool
    observed_at: str | None
    document_id: str | None


class ConditionItem(BaseModel):
    normalized_condition: str
    raw_condition: str | None
    clinical_status: str
    verification_status: str | None


class MedicationItem(BaseModel):
    normalized_medication: str
    raw_medication: str | None
    dose: str | None
    route: str | None
    frequency: str | None
    status: str


class AllergyItem(BaseModel):
    normalized_allergen: str
    raw_allergen: str | None
    reaction: str | None


class PatientSummaryResponse(BaseModel):
    user_id: str
    active_conditions: list[ConditionItem]
    current_medications: list[MedicationItem]
    allergies: list[AllergyItem]
    latest_labs: list[LatestLabItem]


@router.get("/patient/summary", response_model=PatientSummaryResponse)
def get_summary(user_id: str = Depends(get_current_user)):
    """Return aggregated patient summary per D-03/D-07."""
    result = get_patient_summary(user_id)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Nenhum dado clínico encontrado. Faça upload de documentos médicos primeiro.",
        )
    return result
