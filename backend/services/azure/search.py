"""
Search service — indexação e busca RAG por usuário.

Backend: Supabase pgvector (tabela search_index).
Modo mock: busca em memória via BM25 simples.

Isolamento por usuário: todos os documentos têm user_id.
Toda query filtra por user_id — dados nunca se cruzam.
"""
import os
from dataclasses import dataclass, field

_use_mock_cache: bool | None = None


def _use_mock() -> bool:
    global _use_mock_cache
    if _use_mock_cache is None:
        _use_mock_cache = os.getenv("USE_MOCK_AZURE", "true").lower() == "true"
    return _use_mock_cache


@dataclass
class IndexedDocument:
    doc_id: str
    user_id: str
    text: str
    source_name: str
    entities: list[str] = field(default_factory=list)
    content_vector: list[float] | None = None
    document_family: str | None = None
    collection_date: str | None = None
    document_subtype: str | None = None


@dataclass
class SearchResult:
    doc_id: str
    source_name: str
    excerpt: str
    score: float


# Mock: in-memory index
_mock_index: list[IndexedDocument] = []

_supabase_client = None


def _get_supabase_client():
    global _supabase_client
    if _supabase_client is None:
        from supabase import create_client
        _supabase_client = create_client(
            os.environ["SUPABASE_URL"],
            os.environ["SUPABASE_SERVICE_ROLE_KEY"],
        )
    return _supabase_client


def index_document(
    doc_id: str,
    user_id: str,
    text: str,
    source_name: str,
    entities: list[str],
    content_vector: list[float] | None = None,
    document_family: str | None = None,
    collection_date: str | None = None,
    document_subtype: str | None = None,
) -> None:
    """Indexa um documento no search_index (Supabase pgvector) ou mock em memória."""
    if _use_mock():
        global _mock_index
        _mock_index = [d for d in _mock_index if d.doc_id != doc_id]
        _mock_index.append(IndexedDocument(
            doc_id=doc_id,
            user_id=user_id,
            text=text,
            source_name=source_name,
            entities=entities,
            content_vector=content_vector,
            document_family=document_family,
            collection_date=collection_date,
            document_subtype=document_subtype,
        ))
        return

    client = _get_supabase_client()
    row: dict = {
        "id": doc_id,
        "user_id": user_id,
        "content": text,
        "source_name": source_name,
        "entities": ", ".join(entities),
    }
    # Do NOT include None fields — pgvector requires actual vectors, not null strings
    if content_vector is not None:
        row["content_vector"] = content_vector
    if document_family:
        row["document_family"] = document_family
    if collection_date:
        row["collection_date"] = collection_date
    if document_subtype:
        row["document_subtype"] = document_subtype

    client.table("search_index").upsert(row).execute()


def search(
    query: str,
    user_id: str,
    top_k: int = 3,
    query_vector: list[float] | None = None,
) -> list[SearchResult]:
    """
    Busca documentos relevantes para a query do usuário.

    Com query_vector: hybrid search (vector similarity + BM25 via RRF).
    Sem query_vector: full-text search em português.
    Mock: BM25 em memória.
    """
    if _use_mock():
        return _mock_search(query, user_id, top_k)

    client = _get_supabase_client()

    if query_vector is not None:
        response = client.rpc("hybrid_search", {
            "query_text": query,
            "query_embedding": query_vector,
            "user_filter": user_id,
            "top_k": top_k,
        }).execute()
    else:
        response = client.rpc("fts_search", {
            "query_text": query,
            "user_filter": user_id,
            "top_k": top_k,
        }).execute()

    return [
        SearchResult(
            doc_id=r["id"],
            source_name=r["source_name"],
            excerpt=r["content"][:500],
            score=r.get("combined_score", 0.0),
        )
        for r in (response.data or [])
    ]


def _mock_search(query: str, user_id: str, top_k: int) -> list[SearchResult]:
    """Busca por palavras-chave simples nos documentos do usuário."""
    user_docs = [d for d in _mock_index if d.user_id == user_id]
    if not user_docs:
        return []

    query_words = set(query.lower().split())
    scored: list[tuple[float, IndexedDocument]] = []
    for doc in user_docs:
        text_lower = doc.text.lower()
        hits = sum(1 for w in query_words if w in text_lower)
        if hits > 0:
            scored.append((hits / len(query_words), doc))

    scored.sort(key=lambda x: x[0], reverse=True)

    results = []
    for score, doc in scored[:top_k]:
        excerpt = _extract_excerpt(doc.text, query_words)
        results.append(SearchResult(
            doc_id=doc.doc_id,
            source_name=doc.source_name,
            excerpt=excerpt,
            score=score,
        ))
    return results


def _extract_excerpt(text: str, query_words: set[str], max_len: int = 400) -> str:
    text_lower = text.lower()
    best_pos = 0
    for word in query_words:
        pos = text_lower.find(word)
        if pos != -1:
            best_pos = max(0, pos - 100)
            break
    return text[best_pos: best_pos + max_len].strip()
