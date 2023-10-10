import tarfile
import tempfile
from pathlib import Path
from typing import BinaryIO

from httpx import AsyncClient

from .model import CompressMethod, FileSystemInfo

client: AsyncClient | None = None


async def init_client(base_url: str, **kwargs) -> None:
    global client
    client = AsyncClient(base_url=base_url, **kwargs)
    await client.__aenter__()


async def close_client() -> None:
    global client
    if client is not None:
        await client.__aexit__()
        client = None


async def upload(
    directory: str, file: BinaryIO, filename: str, mkdir: bool | None = None, allow_overwrite: bool | None = None
) -> None:
    params = {"directory": directory}
    if mkdir is not None:
        params["mkdir"] = mkdir
    if allow_overwrite is not None:
        params["allow_overwrite"] = allow_overwrite
    files = {"file": (filename, file, "application/octet-stream")}

    response = await client.post("/Upload", files=files, params=params)
    response.raise_for_status()


async def upload_directory(
    parent_dir: str,
    directory: Path | str,
    compress_method: CompressMethod,
    mkdir: bool | None = None,
    zip_metadata_encoding: str | None = None,
) -> None:
    directory = Path(directory)
    with tempfile.SpooledTemporaryFile() as tmp_compress_file:
        match compress_method:
            case CompressMethod.tgz | CompressMethod.txz:
                with tarfile.open(
                    fileobj=tmp_compress_file, mode="w:gz" if compress_method == CompressMethod.tgz else "w:xz"
                ) as tar_file:
                    tar_file.add(directory, arcname=directory.name)
            case _:
                raise ValueError(f"unsupported compress_method: {compress_method}")

        params = {"parent_dir": parent_dir, "compress_method": compress_method}
        if mkdir is not None:
            params["mkdir"] = mkdir
        if zip_metadata_encoding is not None:
            params["zip_metadata_encoding"] = zip_metadata_encoding
        files = {"compressed_dir": (directory.name, tmp_compress_file, "application/octet-stream")}

        response = await client.post("/UploadDirectory", files=files, params=params)
        response.raise_for_status()


async def download_file(path: str, target: BinaryIO | str | Path) -> None:
    response = await client.post("/DownloadFile", params={"path": path})
    response.raise_for_status()

    target_writer = target
    try:
        if isinstance(target, str | Path):
            target_writer = open(target, "wb")
        for chunk in response.iter_bytes(1024 * 1024):
            target_writer.write(chunk)
    finally:
        if isinstance(target, str | Path):
            target_writer.close()


async def download_directory(path: str, target_parent_directory: str | Path) -> None:
    response = await client.post("/DownloadDirectory", params={"path": path})
    response.raise_for_status()

    target_parent_directory = Path(target_parent_directory)
    target_parent_directory.mkdir(parents=True, exist_ok=True)
    tar_file_path = target_parent_directory / f"{path.lstrip('/').replace('/', '_')}.tar.xz"
    try:
        with open(tar_file_path, "wb") as tar_file:
            for chunk in response.iter_bytes(1024 * 1024):
                tar_file.write(chunk)
        with tarfile.open(tar_file_path, "r:xz") as tar_file:
            tar_file.extractall(target_parent_directory)
    finally:
        tar_file_path.unlink(missing_ok=True)


async def delete(path: str, recursive: bool | None = None) -> bool:
    params = {"path": path}
    if recursive is not None:
        params["recursive"] = recursive

    response = await client.post("/Delete", params=params)
    response.raise_for_status()
    return bool(response.text)


async def list_directory(directory: str) -> list[FileSystemInfo]:
    response = await client.post("/List", params={"directory": directory})
    response.raise_for_status()

    return [FileSystemInfo(**info) for info in response.json()]
