import os
import tarfile
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import BinaryIO
from zipfile import ZipFile

from fastapi.responses import FileResponse
from loguru import logger

from zjbs_file_server.settings import settings
from zjbs_file_server.types import AbsoluteUrlPath, CompressMethod, RelativeUrlPath, is_valid_filename
from zjbs_file_server.util import get_os_path, raise_bad_request, raise_not_found


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


def compress(path: Path, compress_method: CompressMethod, follow_symlinks: bool) -> NamedTemporaryFile:
    if follow_symlinks:
        path = path.resolve(strict=True)

    compressed_file = NamedTemporaryFile()
    match compress_method:
        case CompressMethod.zip:
            with ZipFile(compressed_file, mode="w", compresslevel=9) as zip_file:
                if path.is_file():
                    zip_file.write(path, path.name)
                elif path.is_dir():
                    for root, _, files in os.walk(path, followlinks=follow_symlinks):
                        for file in files:
                            file_path = os.path.join(root, file)
                            file_relative_path = os.path.relpath(file_path, path)
                            zip_file.write(file_path, file_relative_path)
                else:
                    logger.error(f"compress fail: not a file or directory: {path}")
                    raise_bad_request("not a file or directory")
        case CompressMethod.tgz | CompressMethod.txz:
            mode = "w:gz" if compress_method == CompressMethod.tgz else "w:xz"
            with tarfile.open(fileobj=compressed_file, mode=mode, dereference=follow_symlinks) as tar_file:
                tar_file.add(path, path.name)
        case _:
            logger.error(f"compress fail: unsupported compress method: {compress_method}")
            raise_bad_request(f"unsupported compress method: {compress_method}")
    return compressed_file


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

    # 写入文件
    try:
        with open(target_path, "wb") as destination_file:
            while chunk := reader.read(settings.BUFFER_SIZE):
                destination_file.write(chunk)
        logger.info(f"upload_file success: {target_path}")
    except IOError:
        logger.exception(f"upload_file fail: io error: {target_path}")
        raise
