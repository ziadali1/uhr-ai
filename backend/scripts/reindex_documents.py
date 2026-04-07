"""
Re-index all documents into Supabase pgvector search_index.

Prerequisite: Run 001_create_search_index.sql in Supabase SQL Editor first.

Usage:
    cd backend
    python scripts/reindex_documents.py --dry-run    # preview only, no writes
    python scripts/reindex_documents.py              # live run
"""
import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

from supabase import create_client
from models.document import StructuredResult
from services.rag.context_block import assemble_context_block
from services.azure.embeddings import generate_embedding
from services.azure.search import index_document


def fetch_all_documents() -> list[dict]:
    """Fetch all documents with non-null anonymized_text from Supabase."""
    client = create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_ROLE_KEY"],
    )
    response = (
        client.table("documents")
        .select("id, user_id, anonymized_text, original_name, structured_result, medical_entities")
        .not_.is_("anonymized_text", "null")
        .execute()
    )
    return response.data or []


def truncate_search_index() -> None:
    """Drop all existing rows — clean slate before re-indexing."""
    client = create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_ROLE_KEY"],
    )
    # Delete all rows (Supabase doesn't expose TRUNCATE via REST; use delete with filter)
    client.table("search_index").delete().neq("id", "").execute()
    logger.info("search_index cleared")


def reindex(dry_run: bool = False) -> None:
    """Re-index all documents into Supabase search_index with pgvector embeddings.

    Args:
        dry_run: If True, preview only — no writes to search_index.
    """
    docs = fetch_all_documents()
    logger.info(f"Found {len(docs)} documents to re-index")

    if not dry_run:
        truncate_search_index()

    total = 0
    embedded = 0
    failed_embed = 0

    for doc in docs:
        doc_id = doc["id"]
        user_id = doc["user_id"]
        anonymized_text = doc.get("anonymized_text") or ""
        source_name = doc.get("original_name") or "unknown"

        # Reconstruct StructuredResult if present
        sr: StructuredResult | None = None
        if doc.get("structured_result"):
            try:
                sr = StructuredResult(**doc["structured_result"])
            except Exception as e:
                logger.warning(f"[{doc_id}] Could not parse structured_result: {e}")

        # Assemble context block (D-01/D-02/D-03)
        context_block = assemble_context_block(sr, anonymized_text)

        # Generate embedding (soft-fail D-10)
        content_vector = generate_embedding(context_block)
        if content_vector is not None:
            embedded += 1
        else:
            failed_embed += 1
            logger.warning(f"[{doc_id}] Embedding failed — indexing without vector")

        # Extract metadata
        document_family = sr.document_family if sr else None
        document_subtype = sr.document_subtype if sr else None
        collection_date = sr.structured_data.get("collection_date") if sr else None

        # Entity labels from medical_entities if available
        entity_labels: list[str] = []
        if doc.get("medical_entities"):
            try:
                entities = doc["medical_entities"]
                if isinstance(entities, list):
                    entity_labels = [
                        f"{e.get('category', '')}: {e.get('text', '')}"
                        for e in entities
                        if isinstance(e, dict)
                    ]
            except Exception:
                pass

        if dry_run:
            vector_status = "vector ok" if content_vector else "no vector"
            logger.info(
                f"[DRY RUN] {doc_id[:8]}... {source_name} | family={document_family} | {vector_status}"
            )
        else:
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

        total += 1

    logger.info(
        "\n%sRe-index complete: %d docs | %d embedded | %d without vector",
        "[DRY RUN] " if dry_run else "",
        total,
        embedded,
        failed_embed,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Re-index all documents into Supabase pgvector")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview only — no writes to search_index",
    )
    args = parser.parse_args()
    reindex(dry_run=args.dry_run)
