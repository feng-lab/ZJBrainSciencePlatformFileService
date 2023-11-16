from pathlib import PurePosixPath
from typing import Annotated

from fastapi import APIRouter, File, Form, Path, Query, UploadFile
from fastapi.responses import FileResponse
from loguru import logger
from starlette.background import BackgroundTask

from zjbs_file_server import service
from zjbs_file_server.types import CompressMethod, FileSystemInfo, RelativeUrlPath
from zjbs_file_server.util import get_os_path, raise_bad_request, raise_not_found

router = APIRouter(tags=["restful"])


@router.get("/restful/{server_path:path}", response_model=None)
async def download_or_list_file(
    server_path: Annotated[RelativeUrlPath, Path(description="文件路径")],
    compress: Annotated[CompressMethod | None, Query(description="压缩方法，文件夹默认txz，文件默认不压缩")] = None,
    follow_symlinks: Annotated[bool, Query(description="是否跟随符号链接")] = True,
    list_: Annotated[bool, Query(alias="list", description="列出文件夹，而非下载文件夹")] = False,
) -> list[FileSystemInfo] | FileResponse:
    file_path = get_os_path(server_path)
    if not file_path.exists():
        logger.error(f"download_file fail: file not exists: {file_path}")
        raise_not_found(server_path)
    if follow_symlinks and file_path.is_symlink():
        file_path = file_path.resolve()

    if list_ and file_path.is_dir():
        return service.list_directory_by_path(server_path, follow_symlinks)

    if compress is None:
        if file_path.is_file():
            return FileResponse(file_path)
        elif file_path.is_dir():
            compress = CompressMethod.txz
        else:
            logger.error(f"download_file fail: unknown file type: {file_path}")
            raise_bad_request(f"unknown file type: {server_path}")

    compressed_file = service.compress(file_path, compress, follow_symlinks)
    return FileResponse(
        compressed_file,
        background=BackgroundTask(compressed_file.unlink, missing_ok=True),
        filename=f"{file_path.stem}.{compress.value}",
    )


@router.post("/restful/{server_path:path}")
async def upload_file(
    server_path: Annotated[RelativeUrlPath, Path(description="目标文件路径")],
    file: Annotated[UploadFile, File(description="上传的文件，忽略文件名")],
    mkdir: Annotated[bool, Form(description="是否创建目录，默认为true")] = True,
    allow_overwrite: Annotated[bool, Form(description="是否允许覆盖已有文件，默认为false")] = False,
):
    pure_path = PurePosixPath(server_path)
    return service.upload_file(str(pure_path.parent), pure_path.name, file.file, mkdir, allow_overwrite)
