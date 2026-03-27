"""
GET /documents — lista documentos do usuário autenticado.
"""
from fastapi import APIRouter, Depends

from models.document import DocumentListResponse, DocumentMetadata
from services.azure.blob_storage import list_user_blobs
from utils.auth import get_current_user
from datetime import datetime, timezone
import uuid

router = APIRouter()


@router.get("/documents", response_model=DocumentListResponse)
def list_documents(user_id: str = Depends(get_current_user)):
    blobs = list_user_blobs(user_id)

    documents = [
        DocumentMetadata(
            id=str(uuid.uuid4()),
            user_id=user_id,
            blob_url=b["url"],
            original_name=b["name"].split("/")[-1],
            file_type="pdf",
            upload_date=datetime.now(timezone.utc),
            entity_count=0,
            anonymized=True,
        )
        for b in blobs
    ]

    return DocumentListResponse(documents=documents, total=len(documents))
