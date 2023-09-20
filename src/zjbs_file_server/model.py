from datetime import datetime
from enum import StrEnum
from typing import Annotated, Self

from pydantic import AfterValidator, BaseModel, model_validator


def url_path(path: str) -> str:
    assert path.startswith("/"), "url path must starts with '/'"
    return path


UrlPath = Annotated[str, AfterValidator(url_path)]


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
