import re
from datetime import datetime
from enum import StrEnum
from typing import Annotated

from pydantic import AfterValidator, BaseModel


def validate_absolute_url_path(path: str) -> str:
    assert path.startswith("/"), "url path must starts with '/'"
    validate_relative_url_path(path[1:])
    return path


def validate_relative_url_path(path: str) -> str:
    assert all(is_valid_filename(part) for part in path.split("/") if part), "url path contains invalid characters"
    return path


AbsoluteUrlPath = Annotated[str, AfterValidator(validate_absolute_url_path)]
RelativeUrlPath = Annotated[str, AfterValidator(validate_relative_url_path)]


class CompressMethod(StrEnum):
    not_compressed = "not_compressed"
    zip = "zip"
    tgz = "tgz"
    txz = "txz"


class FileType(StrEnum):
    file = "file"
    directory = "directory"


class FileSystemInfo(BaseModel):
    type: FileType
    name: str
    last_modified: datetime
    size: int | None = None


def is_valid_filename(filename: str) -> bool:
    return (
        len(filename) <= 255
        and not filename.endswith((".", " "))
        and re.search(r"[/\\{}<>:\"\'|?*\x00\n]", filename) is None
    )
