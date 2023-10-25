import shutil
from pathlib import Path
from tempfile import SpooledTemporaryFile, TemporaryDirectory

import pytest
from zjbs_file_client import CompressMethod, upload, upload_directory

from zjbs_file_server.settings import settings


@pytest.fixture()
async def file() -> SpooledTemporaryFile:
    with SpooledTemporaryFile(mode="w+") as file:
        file.write("test content")
        file.seek(0)
        yield file


async def test_upload(file: SpooledTemporaryFile) -> None:
    uploaded_path = settings.FILE_DIR / "test.txt"
    try:
        await upload("/", file, "test.txt", mkdir=False, allow_overwrite=False)
        assert uploaded_path.read_text() == "test content"
    finally:
        uploaded_path.unlink(missing_ok=True)


@pytest.fixture()
async def directory() -> Path:
    with TemporaryDirectory(prefix="test") as directory:
        dir_path = Path(directory)
        file_path = dir_path / "test.txt"
        file_path.write_text("test content")
        yield dir_path


async def test_upload_directory(directory: Path) -> None:
    uploaded_dir = settings.FILE_DIR / directory.name
    uploaded_file = uploaded_dir / "test.txt"
    try:
        await upload_directory("/", directory, CompressMethod.tgz, mkdir=False)
        assert list(uploaded_dir.iterdir()) == [uploaded_file]
        assert uploaded_file.read_text() == "test content"
    finally:
        shutil.rmtree(uploaded_dir, ignore_errors=True)
