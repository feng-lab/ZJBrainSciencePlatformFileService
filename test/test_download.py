import shutil
from pathlib import Path
from tempfile import SpooledTemporaryFile, TemporaryDirectory

from zjbs_file_client import download_directory, download_file
from zjbs_file_server.util import get_os_path


async def test_download_file():
    url_path = "/test-download/test.txt"
    content = "test content"

    file_path = get_os_path(url_path)
    file_path.parent.mkdir(exist_ok=True, parents=True)
    try:
        file_path.write_text(content)

        with SpooledTemporaryFile() as tmp_file:
            await download_file(url_path, tmp_file)
            tmp_file.seek(0)
            assert tmp_file.read().decode() == content
    finally:
        file_path.unlink(missing_ok=True)


async def test_download_directory():
    dir_url_path = "/test-download-directory"
    file_url_path = f"{dir_url_path}/test.txt"
    content = "test content"

    dir_path, file_path = get_os_path(dir_url_path), get_os_path(file_url_path)
    try:
        dir_path.mkdir(exist_ok=True, parents=True)
        file_path.write_text(content)

        with TemporaryDirectory() as tmp_dir:
            await download_directory(dir_url_path, tmp_dir)
            downloaded_dir = get_os_path(dir_url_path, Path(tmp_dir))
            downloaded_files = list(downloaded_dir.iterdir())
            assert len(downloaded_files) == 1
            downloaded_file = downloaded_files[0]
            assert downloaded_file.read_text() == content
    finally:
        shutil.rmtree(dir_path)
