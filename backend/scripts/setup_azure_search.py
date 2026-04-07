"""
Script de setup: recria o índice no Azure AI Search com schema Phase 4.
Drop + recreate — execute uma vez antes de ligar o servidor em produção.

    cd backend
    python scripts/setup_azure_search.py [--dry-run]
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv()

from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    HnswAlgorithmConfiguration,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SearchableField,
    SemanticConfiguration,
    SemanticField,
    SemanticPrioritizedFields,
    SemanticSearch,
    SimpleField,
    VectorSearch,
    VectorSearchProfile,
)
from azure.core.credentials import AzureKeyCredential

# Constants — defined at module level to prevent profile name mismatch (Pitfall 1)
VECTOR_PROFILE_NAME = "uhr-hnsw-profile"
HNSW_CONFIG_NAME = "uhr-hnsw-config"


def recreate_index(dry_run: bool = False) -> None:
    endpoint = os.environ["SEARCH_ENDPOINT"]
    key = os.environ["SEARCH_KEY"]
    index_name = os.environ.get("SEARCH_INDEX_NAME", "uhr-health-records")

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
        SearchField(
            name="content_vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=1536,
            vector_search_profile_name=VECTOR_PROFILE_NAME,
        ),
        SimpleField(
            name="document_family",
            type=SearchFieldDataType.String,
            filterable=True,
        ),
        SimpleField(
            name="collection_date",
            type=SearchFieldDataType.String,
            filterable=True,
        ),
        SimpleField(
            name="document_subtype",
            type=SearchFieldDataType.String,
            filterable=True,
        ),
    ]

    vector_search = VectorSearch(
        algorithms=[HnswAlgorithmConfiguration(name=HNSW_CONFIG_NAME)],
        profiles=[VectorSearchProfile(
            name=VECTOR_PROFILE_NAME,
            algorithm_configuration_name=HNSW_CONFIG_NAME,  # snake_case per SDK requirement
        )],
    )

    semantic_config = SemanticConfiguration(
        name="uhr-semantic",
        prioritized_fields=SemanticPrioritizedFields(
            content_fields=[SemanticField(field_name="content")],
        ),
    )
    semantic_search = SemanticSearch(configurations=[semantic_config])

    index = SearchIndex(
        name=index_name,
        fields=fields,
        vector_search=vector_search,
        semantic_search=semantic_search,
    )

    if dry_run:
        schema = {
            "name": index.name,
            "fields": [f.name for f in fields],
            "vector_profile": VECTOR_PROFILE_NAME,
            "hnsw_config": HNSW_CONFIG_NAME,
            "semantic_config": "uhr-semantic",
        }
        print("--dry-run: schema preview (no changes made)")
        print(json.dumps(schema, indent=2))
        return

    index_client = SearchIndexClient(endpoint, AzureKeyCredential(key))

    # Drop existing index (ignore if not found)
    try:
        index_client.delete_index(index_name)
        print(f"Dropped existing index '{index_name}'")
    except Exception:
        pass

    index_client.create_or_update_index(index)
    print(f"Index '{index_name}' created with vector + metadata + semantic config.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Recreate Azure AI Search index with Phase 4 schema")
    parser.add_argument("--dry-run", action="store_true", help="Print schema without executing")
    args = parser.parse_args()
    recreate_index(dry_run=args.dry_run)
