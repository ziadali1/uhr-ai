"""
Timeline API — patient observation, condition and medication timeline endpoints.

Exposes the patient query service (Plan 01) via REST per D-04/D-05.
"""
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from utils.auth import get_current_user
from services.patient_query import get_observations_timeline, get_conditions, get_medications

router = APIRouter()


class ObservationTimelineItem(BaseModel):
    observed_at: str | None
    value_num: float | None
    value_str: str | None
    unit: str | None
    ref_low: float | None
    ref_high: float | None
    flag: str | None
    document_id: str | None
    analyte_raw: str | None
    analyte_norm: str | None
    needs_review: bool


class ObservationTimelineResponse(BaseModel):
    analyte: str
    items: list[ObservationTimelineItem]


@router.get("/timeline/observations/{analyte}", response_model=ObservationTimelineResponse)
def get_observation_timeline(
    analyte: str,
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    user_id: str = Depends(get_current_user),
):
    """Return sorted observation timeline for a given analyte per D-04/D-05."""
    items = get_observations_timeline(user_id, analyte, date_from, date_to)
    return ObservationTimelineResponse(analyte=analyte, items=items)


@router.get("/timeline/conditions")
def get_conditions_timeline(user_id: str = Depends(get_current_user)):
    """Return all conditions for the authenticated user."""
    return get_conditions(user_id)


@router.get("/timeline/medications")
def get_medications_timeline(user_id: str = Depends(get_current_user)):
    """Return all medications for the authenticated user."""
    return get_medications(user_id)
