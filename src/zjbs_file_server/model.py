from datetime import datetime
from typing import TypeAlias

from pydantic import BaseModel


class BaseFileSystemInfo(BaseModel):
    name: str
    last_modified: datetime


class FileInfo(BaseFileSystemInfo):
    length: int


class DirectoryInfo(BaseFileSystemInfo):
    pass


FileSystemInfo: TypeAlias = FileInfo | DirectoryInfo
