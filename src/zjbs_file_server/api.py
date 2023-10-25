import os
import shutil
import tarfile
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Self
from zipfile import ZipFile

from fastapi import APIRouter, File, Query, UploadFile
from fastapi.responses import FileResponse
from loguru import logger
from pydantic import AfterValidator, BaseModel, model_validator
from starlette.background import BackgroundTask

from zjbs_file_server.settings import settings
from zjbs_file_server.util import get_os_path, is_valid_filename, raise_bad_request, raise_not_found, validate_url_path

UrlPath = Annotated[str, AfterValidator(validate_url_path)]


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


router = APIRouter(tags=["file"])


@router.post("/Upload", description="上传文件")
def upload_file(
    directory: Annotated[UrlPath, Query(description="目标文件夹")],
    file: Annotated[UploadFile, File(description="上传的文件")],
    mkdir: Annotated[bool, Query(description="是否创建目录")] = False,
    allow_overwrite: Annotated[bool, Query(description="是否允许覆盖已有文件")] = False,
) -> None:
    if not is_valid_filename(file.filename):
        logger.error(f"upload_file fail: invalid filename: {file.filename}")
        raise_bad_request(f"invalid filename: {file.filename}")

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


@router.post("/UploadDirectory", description="以压缩包上传文件夹")
def upload_directory(
    parent_dir: Annotated[UrlPath, Query(description="目标文件夹")],
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


@router.post("/Rename", description="重命名文件")
def rename(
    path: Annotated[UrlPath, Query(description="文件路径")], new_name: Annotated[str, Query(description="新文件名")]
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
