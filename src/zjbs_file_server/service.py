import os
import shutil
import tarfile
import zipfile
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import BinaryIO
from zipfile import ZipFile

from fastapi.responses import FileResponse
from loguru import logger

from zjbs_file_server.types import (
    AbsoluteUrlPath,
    CompressMethod,
    FileSystemInfo,
    FileType,
    RelativeUrlPath,
    is_valid_filename,
)
from zjbs_file_server.util import get_os_path, new_temp_file, raise_bad_request, raise_not_found


def download_file(path: RelativeUrlPath | AbsoluteUrlPath) -> FileResponse:
    file_path = get_os_path(path)
    if not file_path.exists():
        logger.error(f"download_file fail: file not exists: {file_path}")
        raise_not_found(path)
    if not file_path.is_file():
        logger.error(f"download_file fail: not a file: {file_path}")
        raise_bad_request(f"not a file: {path}")

    logger.info(f"download_file success: {file_path}")
    return FileResponse(file_path, filename=file_path.name)


def compress(path: Path, compress_method: CompressMethod, follow_symlinks: bool) -> Path:
    if follow_symlinks:
        path = path.resolve(strict=True)

    compressed_path = new_temp_file()
    match compress_method:
        case CompressMethod.zip:
            with ZipFile(compressed_path, mode="x", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zip_file:
                if path.is_file():
                    zip_file.write(path, path.name)
                elif path.is_dir():
                    parent_path = path.parent
                    for root, _, files in os.walk(path, followlinks=follow_symlinks):
                        for file in files:
                            file_path = os.path.join(root, file)
                            file_relative_path = os.path.relpath(file_path, parent_path)
                            zip_file.write(file_path, file_relative_path)
                else:
                    logger.error(f"compress fail: not a file or directory: {path}")
                    raise_bad_request("not a file or directory")
        case CompressMethod.tgz | CompressMethod.txz:
            mode = "x:gz" if compress_method == CompressMethod.tgz else "x:xz"
            with tarfile.open(compressed_path, mode=mode, dereference=follow_symlinks) as tar_file:
                tar_file.add(path, path.name)
        case _:
            logger.error(f"compress fail: unsupported compress method: {compress_method}")
            raise_bad_request(f"unsupported compress method: {compress_method}")
    return compressed_path


def upload_file(
    target_url_directory: RelativeUrlPath | AbsoluteUrlPath,
    target_filename: str,
    reader: BinaryIO,
    mkdir: bool,
    allow_overwrite: bool,
) -> None:
    # 检查文件夹
    target_directory_path = get_os_path(target_url_directory)
    if not target_directory_path.exists():
        if mkdir:
            target_directory_path.mkdir(parents=True)
        else:
            logger.error(f"upload_file fail: directory not exists: {target_directory_path}")
            raise_bad_request(f"directory {target_url_directory} not exists")

    # 检查文件名
    if not is_valid_filename(target_filename):
        logger.error(f"upload_file fail: invalid filename: {target_filename}")
        raise_bad_request(f"invalid filename: {target_filename}")

    # 检查文件是否已存在
    target_path = target_directory_path / target_filename
    if target_path.exists() and not allow_overwrite:
        logger.error(f"upload_file fail: file already exists: {target_path}")
        raise_bad_request(f"file {target_url_directory}/{target_filename} already exists")

    # 写入临时文件，然后替换为目标文件
    tmp_path = None
    try:
        with NamedTemporaryFile(delete=False, dir=target_directory_path, prefix=target_filename) as tmp_file:
            tmp_path = tmp_file.name
            shutil.copyfileobj(reader, tmp_file)
        os.replace(tmp_path, target_path)
        logger.info(f"upload_file success: {target_path}")
    except (IOError, OSError):
        logger.exception(f"upload_file fail: system error: {target_path}")
        raise
    finally:
        try:
            if tmp_path is not None and os.path.exists(tmp_path):
                os.remove(tmp_path)
        except OSError:
            logger.exception(f"upload_file: remove temp file error: {tmp_path}")


def list_directory_by_path(path: AbsoluteUrlPath | RelativeUrlPath, follow_symlinks: bool) -> list[FileSystemInfo]:
    file_path = get_os_path(path)
    if not file_path.exists():
        logger.error(f"list_directory fail: file not exists: {file_path}")
        raise_not_found(path)
    if file_path.is_symlink() and follow_symlinks:
        file_path = file_path.resolve()
    if not file_path.is_dir():
        logger.error(f"list_directory fail: not directory: {file_path}")
        raise_bad_request(f"{path} is not directory")

    result = []
    for fs_item in file_path.iterdir():
        if fs_item.is_symlink() and follow_symlinks:
            fs_item = fs_item.resolve()
        name = fs_item.name
        last_modified = datetime.fromtimestamp(fs_item.stat().st_mtime)
        if fs_item.is_dir():
            result.append(FileSystemInfo(type=FileType.directory, name=name, last_modified=last_modified))
        elif fs_item.is_file():
            result.append(
                FileSystemInfo(type=FileType.file, name=name, last_modified=last_modified, size=fs_item.stat().st_size)
            )
    return result
