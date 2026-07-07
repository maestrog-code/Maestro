"""
LocalStorageProvider — stores uploaded documents on the local filesystem.

Files are saved under:
    ./uploads/{org_id}/{file_name}

Sprint 005 only. Future sprints will add S3StorageProvider and GCSStorageProvider
by implementing StorageProvider without changing any callers.
"""
import os
import aiofiles
from typing import Optional
from uuid import UUID

from app.ai.storage.base import StorageProvider

# Base directory relative to the working directory of the running process.
# In Docker: /app/uploads/
_UPLOAD_BASE = os.path.join(os.getcwd(), "uploads")


class LocalStorageProvider(StorageProvider):
    """Filesystem-backed storage provider for development / single-node deployments."""

    async def save(self, file_name: str, content: bytes, org_id: UUID, doc_id: Optional[UUID] = None) -> str:
        """
        Save bytes to ./uploads/{org_id}/{doc_id}/{file_name} and return the relative path.
        Using org_id/doc_id subdirectory prevents filename collisions across documents.
        Creates directories if they do not exist.
        """
        # Sanitise file_name to prevent path traversal
        safe_name = os.path.basename(file_name)

        if doc_id:
            sub_dir = os.path.join(_UPLOAD_BASE, str(org_id), str(doc_id))
        else:
            sub_dir = os.path.join(_UPLOAD_BASE, str(org_id))

        os.makedirs(sub_dir, exist_ok=True)
        path = os.path.join(sub_dir, safe_name)

        async with aiofiles.open(path, "wb") as f:
            await f.write(content)

        # Return relative path (not tied to server's absolute path)
        if doc_id:
            return os.path.join(str(org_id), str(doc_id), safe_name)
        return os.path.join(str(org_id), safe_name)


    async def load(self, path: str) -> bytes:
        """
        Load bytes from the given relative storage path.
        Raises FileNotFoundError if the file does not exist.
        """
        abs_path = os.path.join(_UPLOAD_BASE, path)
        if not os.path.exists(abs_path):
            raise FileNotFoundError(f"Storage file not found: {path}")

        async with aiofiles.open(abs_path, "rb") as f:
            return await f.read()

    async def delete(self, path: str) -> None:
        """Delete the file at the given relative storage path (silently ignores missing files)."""
        abs_path = os.path.join(_UPLOAD_BASE, path)
        if os.path.exists(abs_path):
            os.remove(abs_path)

    async def exists(self, path: str) -> bool:
        """Return True if the file exists at the given relative storage path."""
        abs_path = os.path.join(_UPLOAD_BASE, path)
        return os.path.exists(abs_path)


# Module-level singleton — swap this for S3StorageProvider later without touching services.
storage_provider = LocalStorageProvider()
