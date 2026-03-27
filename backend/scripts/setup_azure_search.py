"""
Script de setup único: cria o índice no Azure AI Search.
Execute uma vez antes de ligar o servidor em produção.

    cd backend
    python scripts/setup_azure_search.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv()

from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchField,
    SearchFieldDataType,
    SimpleField,
    SearchableField,
)
from azure.core.credentials import AzureKeyCredential


def create_index() -> None:
    endpoint = os.environ["SEARCH_ENDPOINT"]
    key = os.environ["SEARCH_KEY"]
    index_name = os.environ.get("SEARCH_INDEX_NAME", "uhr-health-records")

    client = SearchIndexClient(endpoint, AzureKeyCredential(key))

    # Verifica se já existe
    existing = [i.name for i in client.list_indexes()]
    if index_name in existing:
        print(f"Índice '{index_name}' já existe. Nada a fazer.")
        return

    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True),
        SimpleField(
            name="user_id",
            type=SearchFieldDataType.String,
            filterable=True,
        ),
        SearchableField(name="content", type=SearchFieldDataType.String),
        SearchableField(name="entities", type=SearchFieldDataType.String),
        SimpleField(
            name="source_name",
            type=SearchFieldDataType.String,
            retrievable=True,
        ),
    ]

    index = SearchIndex(name=index_name, fields=fields)
    client.create_index(index)
    print(f"✅ Índice '{index_name}' criado com sucesso.")


if __name__ == "__main__":
    create_index()
