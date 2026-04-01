"""
/saude — entrada manual de medicamentos, queixas e alergias.

GET  /saude             — lista todas as entradas do usuário
POST /saude             — cria nova entrada + reindexa no RAG
DELETE /saude/{id}      — remove entrada + reindexa no RAG
"""
from fastapi import APIRouter, Depends, HTTPException

from models.health import HealthEntry, HealthEntryCreate
from services import health_store
from utils.auth import get_current_user

router = APIRouter()


@router.get("/saude", response_model=list[HealthEntry])
def list_health_entries(user_id: str = Depends(get_current_user)):
    return health_store.list_by_user(user_id)


@router.post("/saude", response_model=HealthEntry, status_code=201)
def create_health_entry(
    entry: HealthEntryCreate,
    user_id: str = Depends(get_current_user),
):
    created = health_store.create(user_id, entry)
    try:
        health_store.reindex_for_rag(user_id)
    except Exception:
        pass  # RAG indexing failure should not block the response
    return created


@router.delete("/saude/{entry_id}", status_code=204)
def delete_health_entry(entry_id: str, user_id: str = Depends(get_current_user)):
    health_store.delete(entry_id, user_id)
    try:
        health_store.reindex_for_rag(user_id)
    except Exception:
        pass
