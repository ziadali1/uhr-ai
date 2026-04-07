"""Wave 0 test stubs for RETRIEVE-01 — Azure AI Search index schema.

These stubs will fail (skip) until Plan 04-02 implements the schema builder.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import pytest


@pytest.mark.skip(reason="Wave 0 stub — implementation in Plan 02")
def test_index_fields_include_content_vector():
    """Assert that the index schema builder returns a field named content_vector
    with vector_search_dimensions=1536."""
    from services.azure.search_schema import build_index_schema
    schema = build_index_schema()
    field_names = [f.name for f in schema.fields]
    assert "content_vector" in field_names
    vector_field = next(f for f in schema.fields if f.name == "content_vector")
    assert vector_field.vector_search_dimensions == 1536


@pytest.mark.skip(reason="Wave 0 stub — implementation in Plan 02")
def test_index_has_filterable_document_family():
    """Assert document_family field is filterable."""
    from services.azure.search_schema import build_index_schema
    schema = build_index_schema()
    field = next((f for f in schema.fields if f.name == "document_family"), None)
    assert field is not None, "document_family field missing from schema"
    assert field.filterable is True


@pytest.mark.skip(reason="Wave 0 stub — implementation in Plan 02")
def test_index_has_filterable_collection_date():
    """Assert collection_date field is filterable."""
    from services.azure.search_schema import build_index_schema
    schema = build_index_schema()
    field = next((f for f in schema.fields if f.name == "collection_date"), None)
    assert field is not None, "collection_date field missing from schema"
    assert field.filterable is True


@pytest.mark.skip(reason="Wave 0 stub — implementation in Plan 02")
def test_index_has_semantic_config_uhr_semantic():
    """Assert semantic config named uhr-semantic exists."""
    from services.azure.search_schema import build_index_schema
    schema = build_index_schema()
    assert schema.semantic_search is not None
    config_names = [c.name for c in schema.semantic_search.configurations]
    assert "uhr-semantic" in config_names


@pytest.mark.skip(reason="Wave 0 stub — implementation in Plan 02")
def test_vector_search_profile_uses_snake_case():
    """Assert vector search profile uses algorithm_configuration_name (not camelCase)."""
    from services.azure.search_schema import build_index_schema
    schema = build_index_schema()
    assert schema.vector_search is not None
    assert len(schema.vector_search.profiles) > 0
    profile = schema.vector_search.profiles[0]
    # Profile must expose algorithm_configuration_name (snake_case SDK attribute)
    assert hasattr(profile, "algorithm_configuration_name")
