"""Tests for the local-disk ``FileStorage`` implementation.

These use pytest's ``tmp_path`` as the uploads directory, so no database or
external service is required.
"""

from pathlib import Path

from app.integrations.storage.local import LocalFileStorage


def _storage(tmp_path: Path) -> LocalFileStorage:
    return LocalFileStorage(tmp_path)


def test_save_returns_size_matching_written_bytes(tmp_path):
    storage = _storage(tmp_path)
    content = b"%PDF-1.4 pretend resume bytes"

    stored = storage.save(content=content, original_name="resume.pdf")

    assert stored.size == len(content)
    assert stored.key


def test_two_files_named_the_same_do_not_overwrite(tmp_path):
    storage = _storage(tmp_path)

    first = storage.save(content=b"first applicant resume", original_name="resume.pdf")
    second = storage.save(content=b"second applicant resume", original_name="resume.pdf")

    # Distinct stored files, no collision.
    assert first.key != second.key
    assert Path(storage.get_path(first.key)).exists()
    assert Path(storage.get_path(second.key)).exists()

    # Neither write clobbered the other.
    assert storage.read(first.key) == b"first applicant resume"
    assert storage.read(second.key) == b"second applicant resume"


def test_read_returns_exact_bytes_written(tmp_path):
    storage = _storage(tmp_path)
    content = b"\x00\x01\x02 exact binary payload \xff\xfe\xfd"

    stored = storage.save(content=content, original_name="resume.pdf")

    assert storage.read(stored.key) == content


def test_saved_file_lives_inside_uploads_dir(tmp_path):
    storage = _storage(tmp_path)

    stored = storage.save(content=b"data", original_name="resume.pdf")

    resolved = Path(storage.get_path(stored.key)).resolve()
    assert resolved.is_relative_to(tmp_path.resolve())
