from pathlib import PurePosixPath
from typing import Annotated

from fastapi import APIRouter, File, Form, Path, UploadFile
from fastapi.responses import FileResponse

from zjbs_file_server import service
from zjbs_file_server.types import RelativeUrlPath

router = APIRouter(tags=["restful"])


@router.get("/restful/{server_path:path}")
async def download_file(server_path: Annotated[RelativeUrlPath, Path(description="文件路径")]) -> FileResponse:
    return service.download_file(server_path)


@router.post("/restful/{server_path:path}")
async def upload_file(
    server_path: Annotated[RelativeUrlPath, Path(description="目标文件路径")],
    file: Annotated[UploadFile, File(description="上传的文件，忽略文件名")],
    mkdir: Annotated[bool, Form(description="是否创建目录，默认为true")] = True,
    allow_overwrite: Annotated[bool, Form(description="是否允许覆盖已有文件，默认为false")] = False,
):
    pure_path = PurePosixPath(server_path)
    return service.upload_file(str(pure_path.parent), pure_path.name, file.file, mkdir, allow_overwrite)
