import re
from pathlib import Path
from typing import Never

from fastapi import HTTPException
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND, HTTP_500_INTERNAL_SERVER_ERROR

from zjbs_file_server.api import UrlPath
from zjbs_file_server.settings import settings


def raise_not_found(entity: str) -> Never:
    raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=f"{entity} not found")


def raise_bad_request(message: str) -> Never:
    raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=message)


def raise_internal_server_error(message: str) -> Never:
    raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=message)


def get_os_path(url_path: UrlPath) -> Path:
    return settings.FILE_DIR / url_path[1:]


def is_valid_filename(filename: str) -> bool:
    return (
        len(filename) <= 255
        and not filename.endswith((".", " "))
        and re.search(r"[/\\{}<>:\"\'|?*\x00\n]", filename) is None
    )


def validate_url_path(path: str) -> str:
    assert path.startswith("/"), "url path must starts with '/'"
    assert all(is_valid_filename(part) for part in path.split("/") if part), "url path contains invalid characters"
    return path
