import re
from datetime import datetime
from enum import StrEnum
from typing import Annotated, Self

from pydantic import AfterValidator, BaseModel, model_validator


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

    @model_validator(mode="after")
    def validate_type_and_size(self) -> Self:
        match self.type:
            case FileType.file:
                assert self.size is not None, "file size must not be None"
            case FileType.directory:
                assert self.size is None, "directory size must be None"
        return self


def is_valid_filename(filename: str) -> bool:
    return (
        len(filename) <= 255
        and not filename.endswith((".", " "))
        and re.search(r"[/\\{}<>:\"\'|?*\x00\n]", filename) is None
    )
