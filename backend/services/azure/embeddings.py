"""
Azure OpenAI embedding generation — text-embedding-3-small (1536 dims).

Per D-06/D-07: Azure OpenAI only, text-embedding-3-small.
Per D-08: Deployment name from AZURE_OPENAI_EMBEDDING_DEPLOYMENT env var.
         Reuses AZURE_OPENAI_BASE_URL and AZURE_OPENAI_API_KEY.
Per D-10: Soft-fail — failure logs and returns None, never blocks upload.
Per D-24: Mock mode skips embeddings entirely.
"""
import logging
import os

from openai import OpenAI

logger = logging.getLogger(__name__)

_use_mock_cache: bool | None = None


def _use_mock() -> bool:
    global _use_mock_cache
    if _use_mock_cache is None:
        _use_mock_cache = os.getenv("USE_MOCK_AZURE", "true").lower() == "true"
    return _use_mock_cache


def _get_embedding_client() -> OpenAI:
    return OpenAI(
        base_url=os.environ["AZURE_OPENAI_BASE_URL"],
        api_key=os.environ["AZURE_OPENAI_API_KEY"],
    )


def generate_embedding(text: str) -> list[float] | None:
    """Generate a 1536-dim embedding for the given text.

    Returns None if mock mode is active or on any failure (soft-fail per D-10).
    """
    if _use_mock():
        return None

    try:
        deployment = os.environ["AZURE_OPENAI_EMBEDDING_DEPLOYMENT"]
        client = _get_embedding_client()
        response = client.embeddings.create(input=text, model=deployment)
        return response.data[0].embedding
    except Exception as e:
        logger.error("embedding generation failed: %s", e)
        return None
