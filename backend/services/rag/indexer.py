"""
RAG Indexer — called after each upload to index the processed document.

Flow:
  structured_result + anonymized_text -> assemble context block -> generate embedding -> index_document()

Per D-01: embed structured context block, not raw anonymized_text.
Per D-10: embedding failure is soft-fail — document still indexed without vector.
"""
import logging

from models.document import ExtractedEntity, StructuredResult
from services.azure.embeddings import generate_embedding
from services.azure.search import index_document
from services.rag.context_block import assemble_context_block

logger = logging.getLogger(__name__)


def index_after_upload(
    doc_id: str,
    user_id: str,
    anonymized_text: str,
    source_name: str,
    entities: list[ExtractedEntity],
    structured_result: StructuredResult | None = None,
) -> None:
    """
    Index a document in the search index with embedding and metadata.

    1. Assemble context block from structured_result (or fallback to anonymized_text)
    2. Generate embedding from context block (soft-fail per D-10)
    3. Call index_document with text + vector + metadata
    """
    entity_labels = [
        f"{e.category}: {e.text}" + (f" ({e.normalized_text})" if e.normalized_text else "")
        for e in entities
    ]

    # 1. Assemble context block per D-01/D-02/D-03
    context_block = assemble_context_block(structured_result, anonymized_text)

    # 2. Generate embedding (soft-fail per D-10)
    content_vector = generate_embedding(context_block)

    # 3. Extract metadata from structured_result
    document_family: str | None = None
    collection_date: str | None = None
    document_subtype: str | None = None

    if structured_result is not None:
        document_family = structured_result.document_family
        document_subtype = structured_result.document_subtype
        # Extract collection_date from structured_data if available
        collection_date = structured_result.structured_data.get("collection_date")

    # 4. Index with all fields
    index_document(
        doc_id=doc_id,
        user_id=user_id,
        text=anonymized_text,
        source_name=source_name,
        entities=entity_labels,
        content_vector=content_vector,
        document_family=document_family,
        collection_date=collection_date,
        document_subtype=document_subtype,
    )
