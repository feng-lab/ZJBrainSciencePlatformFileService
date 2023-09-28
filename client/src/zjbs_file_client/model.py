from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class FileType(StrEnum):
    file = "file"
    directory = "directory"


@dataclass
class FileSystemInfo:
    type: FileType
    name: str
    last_modified: datetime
    size: int | None
