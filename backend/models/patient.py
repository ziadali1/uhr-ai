from typing import Literal

from pydantic import BaseModel


class PatientObservation(BaseModel):
    """Row model for patient_observations table."""
    user_id: str
    document_id: str | None = None
    normalized_analyte: str
    raw_analyte: str
    value_str: str | None = None
    unit: str | None = None
    reference_range: str | None = None
    flag: Literal["normal", "high", "low", "borderline", "critical"] | None = None
    observed_date: str | None = None   # ISO date string "YYYY-MM-DD"
    needs_review: bool = False


class PatientCondition(BaseModel):
    """Row model for patient_conditions table."""
    user_id: str
    document_id: str | None = None
    raw_condition: str
    normalized_condition: str
    clinical_status: Literal["active", "resolved", "suspected"] | None = None
    verification_status: Literal["confirmed", "provisional"] | None = None


class PatientMedication(BaseModel):
    """Row model for patient_medications table."""
    user_id: str
    document_id: str | None = None
    raw_medication: str
    normalized_medication: str
    dose: str | None = None
    route: str | None = None
    frequency: str | None = None
    status: Literal["active", "stopped"] | None = None


class PatientAllergy(BaseModel):
    """Row model for patient_allergies table."""
    user_id: str
    document_id: str | None = None
    raw_allergen: str
    normalized_allergen: str
    reaction: str | None = None


class PatientImagingFinding(BaseModel):
    """Row model for patient_imaging_findings table."""
    user_id: str
    document_id: str | None = None
    modality: str | None = None
    body_region: str | None = None
    impression: str | None = None
    urgency: Literal["routine", "urgent", "critical"] | None = None
