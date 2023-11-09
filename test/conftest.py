import asyncio

import pytest
from zjbs_file_client import close_client, init_client

from zjbs_file_server.main import app


@pytest.fixture(scope="session", autouse=True)
async def init() -> None:
    await init_client(base_url="http://testserver", app=app, timeout=None)
    yield
    await close_client()


@pytest.fixture(scope="session", autouse=True)
def event_loop() -> asyncio.AbstractEventLoop:
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    loop.set_debug(True)
    yield loop
    loop.close()
