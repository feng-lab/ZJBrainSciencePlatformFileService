from pathlib import Path
from tempfile import SpooledTemporaryFile

import pytest
from fastapi.testclient import TestClient

from zjbs_file_server.util import get_os_path


def test_restful_upload(client: TestClient, temp_file: SpooledTemporaryFile) -> None:
    upload_path = "test/test.txt"
    uploaded_file_path = get_os_path(upload_path)
    try:
        client.post(f"/restful/{upload_path}", files={"file": temp_file}).raise_for_status()

        temp_file.seek(0)
        assert uploaded_file_path.read_text() == temp_file.read()
    finally:
        uploaded_file_path.unlink(missing_ok=True)


@pytest.mark.parametrize("file_server_file", ["/test_restful_download_file/test.txt"], indirect=True)
def test_restful_download_file(client: TestClient, file_server_file: Path) -> None:
    response = client.get("/restful/test_restful_download_file/test.txt").raise_for_status()
    assert response.content == file_server_file.read_bytes()
