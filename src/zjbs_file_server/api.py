import os
import shutil
import tarfile
from pathlib import Path
from typing import Annotated
from zipfile import ZipFile

from fastapi import APIRouter, File, Query, UploadFile
from fastapi.responses import FileResponse
from loguru import logger
from starlette.background import BackgroundTask

from zjbs_file_server import service
from zjbs_file_server.types import AbsoluteUrlPath, CompressMethod, FileSystemInfo, is_valid_filename
from zjbs_file_server.util import get_os_path, raise_bad_request, raise_not_found

router = APIRouter(tags=["file"])


@router.post("/Upload", description="上传文件")
def upload_file(
    directory: Annotated[AbsoluteUrlPath, Query(description="目标文件夹")],
    file: Annotated[UploadFile, File(description="上传的文件")],
    mkdir: Annotated[bool, Query(description="是否创建目录")] = False,
    allow_overwrite: Annotated[bool, Query(description="是否允许覆盖已有文件")] = False,
) -> None:
    return service.upload_file(directory, file.filename, file.file, mkdir, allow_overwrite)


@router.post("/UploadDirectory", description="以压缩包上传文件夹")
def upload_directory(
    parent_dir: Annotated[AbsoluteUrlPath, Query(description="目标文件夹")],
    compressed_dir: Annotated[UploadFile, File(description="上传的文件")],
    compress_method: Annotated[CompressMethod, Query(description="压缩方法")],
    mkdir: Annotated[bool, Query(description="是否创建目录")] = False,
    zip_metadata_encoding: Annotated[str, Query(description="zip文件元数据编码")] = "GB18030",
) -> None:
    destination_parent_dir = get_os_path(parent_dir)
    if mkdir:
        destination_parent_dir.mkdir(parents=True, exist_ok=True)
    elif not destination_parent_dir.is_dir():
        logger.error(f"upload_directory fail: directory not exists or not directory: {destination_parent_dir}")
        raise_bad_request(f"directory {parent_dir} not exists or not directory")

    match compress_method:
        case CompressMethod.zip:
            with ZipFile(compressed_dir.file, mode="r", metadata_encoding=zip_metadata_encoding) as zip_file:
                zip_file.extractall(destination_parent_dir)
        case CompressMethod.tgz | CompressMethod.txz:
            with tarfile.open(
                fileobj=compressed_dir.file, mode="r:gz" if compress_method == CompressMethod.tgz else "r:xz"
            ) as tar_file:
                tar_file.extractall(destination_parent_dir)
        case _:
            logger.error(f"upload_directory fail: unsupported compress method: {compress_method}")
            raise_bad_request(f"unsupported compress method: {compress_method}")
    logger.info(f"upload_zip success: {destination_parent_dir}")


@router.post("/DownloadFile", description="下载文件")
def download_file(path: Annotated[AbsoluteUrlPath, Query(description="文件路径")]) -> FileResponse:
    return service.download_file(path)


@router.post("/DownloadDirectory", description="下载文件夹")
def download_directory(path: Annotated[AbsoluteUrlPath, Query(description="文件路径")]) -> FileResponse:
    dir_path = get_os_path(path)
    if not dir_path.exists():
        logger.error(f"download_directory fail: file not exists: {dir_path}")
        raise_not_found(path)
    if not dir_path.is_dir():
        logger.error(f"download_file fail: not a file: {dir_path}")
        raise_bad_request(f"not a file: {path}")

    compressed = compress_directory(dir_path)
    logger.info(f"download_directory success: {dir_path}")
    return FileResponse(compressed, filename=compressed.name, background=BackgroundTask(os.unlink, compressed))


def compress_directory(dir_path: Path) -> Path:
    compressed = dir_path.with_suffix(".tar.xz")
    with tarfile.open(compressed, "w:xz") as tar_file:
        tar_file.add(dir_path, arcname=dir_path.name)
    return compressed


@router.post("/Delete", description="删除文件")
def delete_file(
    path: Annotated[AbsoluteUrlPath, Query(description="文件路径")],
    recursive: Annotated[bool, Query(description="是否递归删除")] = False,
) -> bool:
    file_path = get_os_path(path)
    if not file_path.exists():
        logger.error(f"delete file fail: file not exists: {file_path}")
        return False
    if file_path.is_file():
        file_path.unlink()
        logger.info(f"delete file success: {file_path}")
        return True
    if file_path.is_dir():
        if recursive:
            shutil.rmtree(file_path)
            logger.info(f"delete directory success: {file_path}")
            return True
        else:
            try:
                file_path.rmdir()
                logger.info(f"delete empty directory success: {file_path}")
                return True
            except OSError:
                logger.error(f"delete empty directory fail: {file_path}")
                return False


@router.post("/List", description="获取文件列表")
def list_directory(directory: Annotated[AbsoluteUrlPath, Query(description="文件路径")]) -> list[FileSystemInfo]:
    return service.list_directory_by_path(directory, True)


@router.post("/Rename", description="重命名文件")
def rename(
    path: Annotated[AbsoluteUrlPath, Query(description="文件路径")],
    new_name: Annotated[str, Query(description="新文件名")],
) -> None:
    file_path = get_os_path(path)
    if not file_path.exists():
        logger.error(f"rename fail: file not exists: {path}")
        raise_not_found(path)
    if not is_valid_filename(new_name):
        logger.error(f"rename fail: invalid filename: {new_name}")
        raise_bad_request(f"invalid filename: {new_name}")
    new_path = file_path.parent / new_name
    if new_path.exists():
        logger.error(f"rename fail: target exists: {new_path}")
        raise_bad_request(f"target exists: {new_name}")

    os.rename(file_path, new_path)
