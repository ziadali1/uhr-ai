"""
RAG Indexer — chamado após cada upload para indexar o documento processado.

Fluxo:
  documento anonimizado → extrai textos de entidades → index_document()
"""
from models.document import ExtractedEntity
from services.azure.search import index_document


def index_after_upload(
    doc_id: str,
    user_id: str,
    anonymized_text: str,
    source_name: str,
    entities: list[ExtractedEntity],
) -> None:
    """
    Indexa o texto anonimizado de um documento no Azure AI Search.
    Chamado automaticamente pelo endpoint POST /upload após a anonimização.
    """
    entity_labels = [
        f"{e.category}: {e.text}" + (f" ({e.normalized_text})" if e.normalized_text else "")
        for e in entities
    ]

    index_document(
        doc_id=doc_id,
        user_id=user_id,
        text=anonymized_text,
        source_name=source_name,
        entities=entity_labels,
    )
