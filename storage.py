# apps/api/storage.py
import os
from azure.storage.blob import BlobServiceClient, ContentSettings

def _client():
    conn = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    if conn:
        return BlobServiceClient.from_connection_string(conn)
    acc  = os.getenv("AZURE_STORAGE_ACCOUNT")
    key  = os.getenv("AZURE_STORAGE_KEY")
    if acc and key:
        return BlobServiceClient(account_url=f"https://{acc}.blob.core.windows.net", credential=key)
    return None

def configured() -> bool:
    return _client() is not None

def upload_bytes(blob_path: str, data: bytes, content_type: str | None = None) -> str:
    container = os.getenv("BLOBDROP_CONTAINER", "blobdrop")
    svc = _client()
    if not svc:
        raise RuntimeError("Azure storage not configured")
    cc = svc.get_container_client(container)
    try:
        cc.create_container()
    except Exception:
        pass  # already exists
    bc = cc.get_blob_client(blob_path)
    cs = ContentSettings(content_type=content_type) if content_type else None
    bc.upload_blob(data, overwrite=True, content_settings=cs)
    return bc.url
