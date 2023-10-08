import os
import shutil
import tarfile
from datetime import datetime
from pathlib import Path
from typing import Annotated
from zipfile import ZipFile

from fastapi import APIRouter, File, Query, UploadFile
from fastapi.responses import FileResponse
from loguru import logger
from starlette.background import BackgroundTask

from zjbs_file_server.error import raise_bad_request, raise_not_found
from zjbs_file_server.model import FileSystemInfo, FileType, UrlPath
from zjbs_file_server.settings import settings

router = APIRouter(tags=["file"])


@router.post("/Upload", description="上传文件")
def upload_file(
    directory: Annotated[UrlPath, Query(description="目标文件夹")],
    file: Annotated[UploadFile, File(description="上传的文件")],
    mkdir: Annotated[bool, Query(description="是否创建目录")] = False,
    allow_overwrite: Annotated[bool, Query(description="是否允许覆盖已有文件")] = False,
) -> None:
    destination_folder = get_os_path(directory)
    if not destination_folder.exists():
        if mkdir:
            destination_folder.mkdir(parents=True)
        else:
            logger.error(f"upload_file fail: directory not exists: {destination_folder}")
            raise_bad_request(f"directory {directory} not exists")

    destination_path = destination_folder / file.filename
    if destination_path.exists() and not allow_overwrite:
        logger.error(f"upload_file fail: file already exists: {destination_path}")
        raise_bad_request(f"file {directory}/{file.filename} already exists")

    try:
        with open(destination_path, "wb") as destination_file:
            while chunk := file.file.read(settings.BUFFER_SIZE):
                destination_file.write(chunk)
        logger.info(f"upload_file success: {destination_path}")
    except IOError:
        logger.exception(f"upload_file fail: io error: {destination_path}")
        raise


@router.post("/UploadZip", description="上传并解压缩zip文件")
def upload_zip(
    directory: Annotated[UrlPath, Query(description="目标文件夹")],
    file: Annotated[UploadFile, File(description="上传的文件")],
    mkdir: Annotated[bool, Query(description="是否创建目录")] = False,
    allow_overwrite: Annotated[bool, Query(description="是否允许覆盖已有文件")] = False,
    zip_metadata_encoding: Annotated[str, Query(description="zip文件元数据编码")] = "GB18030",
) -> None:
    upload_file(directory, file, mkdir, allow_overwrite)

    destination_dir = get_os_path(directory)
    zip_path = destination_dir / file.filename
    with ZipFile(zip_path, mode="r", metadata_encoding=zip_metadata_encoding) as zip_file:
        zip_file.extractall(destination_dir)

    zip_path.unlink()
    logger.info(f"upload_zip success: {destination_dir}")


@router.post("/DownloadFile", description="下载文件")
def download_file(path: Annotated[UrlPath, Query(description="文件路径")]) -> FileResponse:
    file_path = get_os_path(path)
    if not file_path.exists():
        logger.error(f"download_file fail: file not exists: {file_path}")
        raise_not_found(path)
    if not file_path.is_file():
        logger.error(f"download_file fail: not a file: {file_path}")
        raise_bad_request(f"not a file: {path}")

    logger.info(f"download_file success: {file_path}")
    return FileResponse(file_path, filename=file_path.name)


@router.post("/DownloadDirectory", description="下载文件夹")
def download_directory(path: Annotated[UrlPath, Query(description="文件路径")]) -> FileResponse:
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
    path: Annotated[UrlPath, Query(description="文件路径")], recursive: Annotated[bool, Query(description="是否递归删除")] = False
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
def list_directory(directory: Annotated[UrlPath, Query(description="文件路径")]) -> list[FileSystemInfo]:
    file_path = get_os_path(directory)
    if not file_path.exists():
        logger.error(f"list_directory fail: file not exists: {file_path}")
        raise_not_found(directory)
    if not file_path.is_dir():
        logger.error(f"list_directory fail: not directory: {file_path}")
        raise_bad_request(f"{directory} is not directory")

    result = []
    for fs_item in file_path.iterdir():
        name = fs_item.name
        last_modified = datetime.fromtimestamp(fs_item.stat().st_mtime)
        if fs_item.is_dir():
            result.append(FileSystemInfo(type=FileType.directory, name=name, last_modified=last_modified))
        if fs_item.is_file():
            result.append(
                FileSystemInfo(type=FileType.file, name=name, last_modified=last_modified, size=fs_item.stat().st_size)
            )
    return result


def get_os_path(url_path: UrlPath) -> Path:
    return settings.FILE_DIR / url_path[1:]
