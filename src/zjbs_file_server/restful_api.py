from typing import Annotated

from fastapi import APIRouter, File, Path, UploadFile
from loguru import logger

from zjbs_file_server.types import RelativeUrlPath

router = APIRouter(tags=["restful"])


@router.get("/restful/{server_path:path}")
async def download_file(server_path: Annotated[RelativeUrlPath, Path(description="文件路径")]):
    logger.debug(f"{server_path=}")
    return {"path": server_path}


@router.post("/restful/{server_path:path}")
async def upload_file(
    server_path: Annotated[RelativeUrlPath, Path(description="文件路径")],
    file: Annotated[UploadFile, File(description="上传的文件")],
):
    logger.debug(f"{server_path=}, uploaded_file={file.filename}, uploaded_file.size={file.size}")
    return {"path": server_path, "filename": file.filename, "file_size": file.size}
