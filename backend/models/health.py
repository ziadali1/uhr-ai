from datetime import date, datetime
from enum import Enum
from pydantic import BaseModel


class HealthEntryType(str, Enum):
    medication_current = "medication_current"
    medication_past    = "medication_past"
    complaint          = "complaint"
    allergy            = "allergy"


class HealthEntryCreate(BaseModel):
    entry_type: HealthEntryType
    name: str
    details: str | None = None
    started_at: date | None = None
    ended_at: date | None = None


class HealthEntry(HealthEntryCreate):
    id: str
    user_id: str
    active: bool
    created_at: datetime
