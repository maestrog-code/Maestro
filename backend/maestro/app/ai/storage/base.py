"""
StorageProvider — abstract interface for document file storage.

Mirrors the BaseLLMProvider pattern from Sprint 004.
Sprint 005 implements LocalStorageProvider only.
Future sprints can add S3StorageProvider, GCSStorageProvider without changing callers.
"""
from abc import ABC, abstractmethod
from uuid import UUID


class StorageProvider(ABC):
    """Abstract base class for all storage backends."""

    @abstractmethod
    async def save(self, file_name: str, content: bytes, org_id: UUID) -> str:
        """
        Persist file bytes and return the storage path.

        Args:
            file_name: Original filename (used to derive extension / storage key).
            content:   Raw file bytes.
            org_id:    Organization UUID — used to namespace the storage path.

        Returns:
            A string path/key that can be passed back to load() or delete().
        """
        pass

    @abstractmethod
    async def load(self, path: str) -> bytes:
        """
        Retrieve raw bytes from the given storage path.

        Args:
            path: The path/key returned by save().

        Returns:
            Raw file bytes.

        Raises:
            FileNotFoundError: If the path does not exist in storage.
        """
        pass

    @abstractmethod
    async def delete(self, path: str) -> None:
        """
        Delete the file at the given storage path.

        Args:
            path: The path/key returned by save().
        """
        pass

    @abstractmethod
    async def exists(self, path: str) -> bool:
        """
        Check whether a file exists at the given storage path.

        Args:
            path: The path/key returned by save().

        Returns:
            True if the file exists, False otherwise.
        """
        pass
