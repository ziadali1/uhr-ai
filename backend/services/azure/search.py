"""
Azure AI Search — indexação e busca RAG por usuário.

Estratégia de isolamento: índice único com campo user_id em todos os documentos.
Toda query inclui filter=user_id eq '{user_id}' — dados de usuários nunca se cruzam.

Modo produção: busca por keyword (full-text) — sem embeddings, sem custo adicional.
Modo mock: busca em memória.
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


@dataclass
class SearchResult:
    doc_id: str
    source_name: str
    excerpt: str
    score: float


# Mock: lista de documentos indexados em memória
_mock_index: list[IndexedDocument] = []


def index_document(
    doc_id: str,
    user_id: str,
    text: str,
    source_name: str,
    entities: list[str],
) -> None:
    """Indexa um documento no Azure AI Search (ou mock em memória)."""
    if _use_mock():
        # Remove versão anterior do mesmo doc_id se existir
        global _mock_index
        _mock_index = [d for d in _mock_index if d.doc_id != doc_id]
        _mock_index.append(IndexedDocument(
            doc_id=doc_id,
            user_id=user_id,
            text=text,
            source_name=source_name,
            entities=entities,
        ))
        return

    from azure.search.documents import SearchClient
    from azure.core.credentials import AzureKeyCredential

    endpoint = os.environ["SEARCH_ENDPOINT"]
    key = os.environ["SEARCH_KEY"]
    index_name = os.environ.get("SEARCH_INDEX_NAME", "uhr-health-records")

    client = SearchClient(endpoint, index_name, AzureKeyCredential(key))
    client.upload_documents(documents=[{
        "id": doc_id,
        "user_id": user_id,
        "content": text,
        "source_name": source_name,
        "entities": ", ".join(entities),
    }])


def search(query: str, user_id: str, top_k: int = 3) -> list[SearchResult]:
    """
    Busca documentos relevantes para a query do usuário.
    Retorna os top_k resultados filtrados pelo user_id.
    """
    if _use_mock():
        return _mock_search(query, user_id, top_k)

    from azure.search.documents import SearchClient
    from azure.core.credentials import AzureKeyCredential

    endpoint = os.environ["SEARCH_ENDPOINT"]
    key = os.environ["SEARCH_KEY"]
    index_name = os.environ.get("SEARCH_INDEX_NAME", "uhr-health-records")

    client = SearchClient(endpoint, index_name, AzureKeyCredential(key))

    results = client.search(
        search_text=query,
        filter=f"user_id eq '{user_id}'",
        top=top_k,
        select=["id", "content", "source_name"],
    )

    return [
        SearchResult(
            doc_id=r["id"],
            source_name=r["source_name"],
            excerpt=r["content"][:500],
            score=r["@search.score"],
        )
        for r in results
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
        # Score = proporção de palavras da query encontradas no texto
        hits = sum(1 for w in query_words if w in text_lower)
        if hits > 0:
            scored.append((hits / len(query_words), doc))

    scored.sort(key=lambda x: x[0], reverse=True)

    results = []
    for score, doc in scored[:top_k]:
        # Extrai trecho relevante ao redor da primeira palavra encontrada
        excerpt = _extract_excerpt(doc.text, query_words)
        results.append(SearchResult(
            doc_id=doc.doc_id,
            source_name=doc.source_name,
            excerpt=excerpt,
            score=score,
        ))

    return results


def _extract_excerpt(text: str, query_words: set[str], max_len: int = 400) -> str:
    """Extrai um trecho do texto próximo às palavras da query."""
    text_lower = text.lower()
    best_pos = 0
    for word in query_words:
        pos = text_lower.find(word)
        if pos != -1:
            best_pos = max(0, pos - 100)
            break
    return text[best_pos: best_pos + max_len].strip()


