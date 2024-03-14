import shutil
from pathlib import Path
from tempfile import SpooledTemporaryFile, TemporaryDirectory

import pytest

from zjbs_file_server.util import get_os_path


@pytest.fixture()
def temp_file() -> SpooledTemporaryFile:
    with SpooledTemporaryFile(mode="w+") as file:
        file.write("test content")
        file.seek(0)
        yield file


@pytest.fixture()
def temp_directory() -> Path:
    with TemporaryDirectory(prefix="test") as directory:
        dir_path = Path(directory)
        file_path = dir_path / "test.txt"
        file_path.write_text("test content")
        yield dir_path


@pytest.fixture()
def file_server_file(request) -> Path:
    file_path = get_os_path(request.param)
    file_path.parent.mkdir(exist_ok=True, parents=True)
    try:
        file_path.write_text("test content")
        yield file_path
    finally:
        file_path.unlink(missing_ok=True)


@pytest.fixture()
def file_server_directory(request) -> Path:
    dir_path = get_os_path(request.param)
    try:
        dir_path.mkdir(exist_ok=True, parents=True)
        yield dir_path
    finally:
        shutil.rmtree(dir_path)
