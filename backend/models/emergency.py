from datetime import datetime
from pydantic import BaseModel


class Allergy(BaseModel):
    name: str
    severity: str  # "leve", "moderada", "severa"


class Medication(BaseModel):
    name: str
    dose: str
    alert: str | None = None  # ex: "risco cirúrgico"


class EmergencyProfile(BaseModel):
    user_id: str
    blood_type: str | None = None
    allergies: list[Allergy] = []
    active_medications: list[Medication] = []
    active_conditions: list[str] = []
    last_updated: datetime
