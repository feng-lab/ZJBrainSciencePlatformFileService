import asyncio
import shutil
from pathlib import Path
from tempfile import SpooledTemporaryFile, TemporaryDirectory

import pytest
from fastapi.testclient import TestClient

from zjbs_file_client import close_client, init_client
from zjbs_file_server.main import app
from zjbs_file_server.util import get_os_path


@pytest.fixture(scope="session", autouse=True)
async def init() -> None:
    await init_client(base_url="http://testserver", app=app, timeout=None)
    yield
    await close_client()


@pytest.fixture()
def client() -> TestClient:
    with TestClient(app) as client:
        yield client


@pytest.fixture(scope="session", autouse=True)
def event_loop() -> asyncio.AbstractEventLoop:
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    loop.set_debug(True)
    yield loop
    loop.close()


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
