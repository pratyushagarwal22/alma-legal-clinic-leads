"""File storage integration interface.

Storage is an integration behind an interface so implementations (local disk now,
S3 later) can be swapped without touching business logic. Per the design's
layering rules this is called only from the service layer, never from routers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class StoredFile:
    """Metadata for a persisted file.

    ``key`` is the opaque reference (stored path/key) used to read the file back;
    the database stores this, never the bytes. ``size`` is the number of bytes
    written.
    """

    key: str
    size: int


class FileStorage(ABC):
    """Interface for persisting and retrieving uploaded files."""

    @abstractmethod
    def save(self, *, content: bytes, original_name: str) -> StoredFile:
        """Persist ``content`` under a unique key derived from ``original_name``.

        Returns the stored key plus the number of bytes written. Two files sharing
        the same ``original_name`` must never overwrite each other.
        """

    @abstractmethod
    def get_path(self, key: str) -> str:
        """Resolve a stored ``key`` to a concrete location reference."""

    @abstractmethod
    def read(self, key: str) -> bytes:
        """Load and return the exact bytes previously stored under ``key``."""
