import shutil
from pathlib import Path
from tempfile import SpooledTemporaryFile, TemporaryDirectory

import pytest

from zjbs_file_client import AsyncClient, CompressMethod
from zjbs_file_server.main import app
from zjbs_file_server.settings import settings
from zjbs_file_server.util import get_os_path


@pytest.mark.parametrize("file_server_file", ["/test_download_file/test.txt"], indirect=True)
async def test_download_file(file_server_file: Path):
    async with AsyncClient(base_url="http://testserver", app=app, timeout=None) as client:
        with SpooledTemporaryFile() as tmp_file:
            await client.download_file("/test_download_file/test.txt", tmp_file)
            tmp_file.seek(0)
            assert tmp_file.read() == file_server_file.read_bytes()


@pytest.mark.parametrize("file_server_file", ["/test_download_directory/test.txt"], indirect=True)
async def test_download_directory(file_server_file: Path):
    async with AsyncClient(base_url="http://testserver", app=app, timeout=None) as client:
        with TemporaryDirectory() as tmp_dir:
            await client.download_directory("/test_download_directory", tmp_dir)
            downloaded_dir = get_os_path("/test_download_directory", Path(tmp_dir))
            downloaded_files = list(downloaded_dir.iterdir())
            assert len(downloaded_files) == 1
            downloaded_file = downloaded_files[0]
            assert downloaded_file.read_text() == file_server_file.read_text()


async def test_upload(temp_file: SpooledTemporaryFile) -> None:
    async with AsyncClient(base_url="http://testserver", app=app, timeout=None) as client:
        uploaded_path = settings.FILE_DIR / "test.txt"
        try:
            await client.upload("/", temp_file, "test.txt", mkdir=False, allow_overwrite=False)
            assert uploaded_path.read_text() == "test content"
        finally:
            uploaded_path.unlink(missing_ok=True)


async def test_upload_directory(temp_directory: Path) -> None:
    async with AsyncClient(base_url="http://testserver", app=app, timeout=None) as client:
        uploaded_dir = settings.FILE_DIR / temp_directory.name
        uploaded_file = uploaded_dir / "test.txt"
        try:
            await client.upload_directory("/", temp_directory, CompressMethod.tgz, mkdir=False)
            assert list(uploaded_dir.iterdir()) == [uploaded_file]
            assert uploaded_file.read_text() == "test content"
        finally:
            shutil.rmtree(uploaded_dir, ignore_errors=True)
