"""
Azure Blob Storage — upload, download e listagem de documentos médicos.
Com USE_MOCK_AZURE=true, opera em memória sem Azure real.
"""
import os
import uuid
from datetime import datetime
from io import BytesIO

_mock_store: dict[str, bytes] = {}


def _use_mock() -> bool:
    return os.getenv("USE_MOCK_AZURE", "true").lower() == "true"


def upload_blob(file_bytes: bytes, filename: str, user_id: str) -> str:
    """
    Faz upload de um arquivo para o Blob Storage.
    Retorna a URL (ou chave mock) do blob criado.
    """
    blob_name = f"{user_id}/{uuid.uuid4()}/{filename}"

    if _use_mock():
        _mock_store[blob_name] = file_bytes
        return f"mock://health-records/{blob_name}"

    from azure.storage.blob import BlobServiceClient

    conn_str = os.environ["AZURE_STORAGE_CONNECTION_STRING"]
    container = os.environ["STORAGE_CONTAINER_NAME"]

    client = BlobServiceClient.from_connection_string(conn_str)
    blob_client = client.get_blob_client(container=container, blob=blob_name)
    blob_client.upload_blob(BytesIO(file_bytes), overwrite=True)

    return blob_client.url


def download_blob(blob_url: str) -> bytes:
    """Faz download de um blob pelo URL (ou chave mock)."""
    if _use_mock():
        key = blob_url.removeprefix("mock://health-records/")
        return _mock_store.get(key, b"")

    from azure.storage.blob import BlobClient

    blob_client = BlobClient.from_blob_url(blob_url)
    return blob_client.download_blob().readall()


def list_user_blobs(user_id: str) -> list[dict]:
    """Lista todos os blobs de um usuário com metadados básicos."""
    if _use_mock():
        return [
            {"name": k, "url": f"mock://health-records/{k}", "size": len(v)}
            for k, v in _mock_store.items()
            if k.startswith(f"{user_id}/")
        ]

    from azure.storage.blob import BlobServiceClient

    conn_str = os.environ["AZURE_STORAGE_CONNECTION_STRING"]
    container = os.environ["STORAGE_CONTAINER_NAME"]

    client = BlobServiceClient.from_connection_string(conn_str)
    container_client = client.get_container_client(container)

    blobs = []
    for blob in container_client.list_blobs(name_starts_with=f"{user_id}/"):
        blobs.append({
            "name": blob.name,
            "url": f"https://{client.account_name}.blob.core.windows.net/{container}/{blob.name}",
            "size": blob.size,
        })
    return blobs
