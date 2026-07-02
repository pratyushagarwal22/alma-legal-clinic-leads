"""Local-disk implementation of the ``FileStorage`` interface.

Files are written under ``UPLOADS_DIR`` using a unique, collision-proof name so
two uploads sharing an original filename never overwrite each other. The original
extension is preserved on the stored key to aid content serving later. Only the
opaque key is meant to be persisted (in the DB); ``read`` loads the bytes back.
"""

import uuid
from pathlib import Path

from app.integrations.storage.base import FileStorage, StoredFile


class LocalFileStorage(FileStorage):
    def __init__(self, uploads_dir: str | Path) -> None:
        self._root = Path(uploads_dir)
        self._root.mkdir(parents=True, exist_ok=True)

    def save(self, *, content: bytes, original_name: str) -> StoredFile:
        key = f"{uuid.uuid4().hex}{Path(original_name).suffix}"
        self._root.joinpath(key).write_bytes(content)
        return StoredFile(key=key, size=len(content))

    def get_path(self, key: str) -> str:
        return str(self._root / key)

    def read(self, key: str) -> bytes:
        return (self._root / key).read_bytes()
