from typing import Annotated

from fastapi import APIRouter, File, Query, UploadFile
from fastapi.responses import FileResponse
from loguru import logger

from zjbs_file_server.model import FileSystemInfo

router = APIRouter(prefix="/file", tags=["file"])


@router.post("/upload", description="上传文件")
def upload_file(
    directory: Annotated[str, Query(description="目标文件夹")], file: Annotated[UploadFile, File(description="上传的文件")]
) -> bool:
    logger.debug(f"{directory=}")
    logger.debug(f"{file.filename}, {file.content_type=}")
    return True


@router.post("/download", description="下载文件")
def download_file(path: Annotated[str, Query(description="文件路径")]) -> FileResponse:
    logger.debug(f"{path=}")
    return {}


@router.post("/delete", description="删除文件")
def delete_file(path: Annotated[str, Query(description="文件路径")]) -> bool:
    logger.debug(f"{path=}")
    return True


@router.post("/list", description="获取文件列表")
def list_directory(directory: Annotated[str, Query(description="文件路径")]) -> list[FileSystemInfo]:
    logger.debug(f"{directory=}")
    return []
