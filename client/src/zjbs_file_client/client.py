import tarfile
import tempfile
from contextlib import contextmanager
from io import IOBase
from pathlib import Path

import httpx
from httpx import Response

# noinspection PyProtectedMember
from httpx._types import FileTypes, QueryParamTypes, RequestFiles

from .model import CompressMethod, FileSystemInfo


def _prepare_upload(
    directory: str, file: FileTypes, filename: str, mkdir: bool | None, allow_overwrite: bool | None
) -> tuple[RequestFiles, QueryParamTypes]:
    params = {"directory": directory}
    if mkdir is not None:
        params["mkdir"] = mkdir
    if allow_overwrite is not None:
        params["allow_overwrite"] = allow_overwrite
    files = {"file": (filename, file, "application/octet-stream")}
    return files, params


@contextmanager
def _prepare_upload_directory(
    parent_dir: str,
    directory: Path | str,
    compress_method: CompressMethod,
    mkdir: bool | None,
    zip_metadata_encoding: str | None,
) -> tuple[RequestFiles, QueryParamTypes]:
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
        yield files, params


def _finish_download(response: Response, target: IOBase | str | Path) -> None:
    target_writer = target
    try:
        if isinstance(target, str | Path):
            target_writer = open(target, "wb")
        for chunk in response.iter_bytes(1024 * 1024):
            target_writer.write(chunk)
    finally:
        if isinstance(target, str | Path):
            target_writer.close()


def _finish_download_directory(response: Response, path: str, target_parent_directory: str | Path) -> Path:
    target_parent_directory = Path(target_parent_directory)
    target_parent_directory.mkdir(parents=True, exist_ok=True)
    tar_file_path = target_parent_directory / f"{path.lstrip('/').replace('/', '_')}.tar.xz"
    try:
        with open(tar_file_path, "wb") as tar_file:
            for chunk in response.iter_bytes(1024 * 1024):
                tar_file.write(chunk)
        with tarfile.open(tar_file_path, "r:xz") as tar_file:
            tar_file.extractall(target_parent_directory)
        return target_parent_directory / path.rstrip("/").rsplit("/", 1)[1]
    finally:
        tar_file_path.unlink(missing_ok=True)


def _prepare_delete(path: str, recursive: bool | None) -> QueryParamTypes:
    params = {"path": path}
    if recursive is not None:
        params["recursive"] = recursive
    return params


def _finish_list_directory(response: Response) -> list[FileSystemInfo]:
    return [FileSystemInfo(**info) for info in response.json()]


class AsyncClient:
    def __init__(self, base_url: str, **kwargs):
        self.inner = httpx.AsyncClient(base_url=base_url, **kwargs)

    async def __aenter__(self):
        await self.inner.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.inner.__aexit__(exc_type, exc_val, exc_tb)

    async def upload(
        self,
        directory: str,
        file: FileTypes,
        filename: str,
        mkdir: bool | None = None,
        allow_overwrite: bool | None = None,
    ) -> None:
        files, params = _prepare_upload(directory, file, filename, mkdir, allow_overwrite)
        response = await self.inner.post("/upload-file", files=files, params=params)
        response.raise_for_status()

    async def upload_directory(
        self,
        parent_dir: str,
        directory: Path | str,
        compress_method: CompressMethod,
        mkdir: bool | None = None,
        zip_metadata_encoding: str | None = None,
    ) -> None:
        with _prepare_upload_directory(parent_dir, directory, compress_method, mkdir, zip_metadata_encoding) as (
            files,
            params,
        ):
            response = await self.inner.post("/upload-directory", files=files, params=params)
            response.raise_for_status()

    async def download_file(self, path: str, target: IOBase | str | Path) -> None:
        response = await self.inner.post("/download-file", params={"path": path})
        response.raise_for_status()
        _finish_download(response, target)

    async def download_directory(self, path: str, target_parent_directory: str | Path) -> Path:
        response = await self.inner.post("/download-directory", params={"path": path})
        response.raise_for_status()
        return _finish_download_directory(response, path, target_parent_directory)

    async def delete(self, path: str, recursive: bool | None = None) -> bool:
        params = _prepare_delete(path, recursive)
        response = await self.inner.post("/delete", params=params)
        response.raise_for_status()
        return bool(response.text)

    async def list_directory(self, directory: str) -> list[FileSystemInfo]:
        response = await self.inner.post("/list-directory", params={"directory": directory})
        response.raise_for_status()
        return _finish_list_directory(response)

    async def rename(self, path: str, new_name: str) -> None:
        response = await self.inner.post("/rename", params={"path": path, "new_name": new_name})
        response.raise_for_status()


class Client:
    def __init__(self, base_url: str, **kwargs):
        self.inner = httpx.Client(base_url=base_url, **kwargs)

    def __enter__(self):
        self.inner.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self.inner.__exit__(exc_type, exc_val, exc_tb)

    def upload(
        self,
        directory: str,
        file: FileTypes,
        filename: str,
        mkdir: bool | None = None,
        allow_overwrite: bool | None = None,
    ) -> None:
        files, params = _prepare_upload(directory, file, filename, mkdir, allow_overwrite)
        response = self.inner.post("/upload-file", files=files, params=params)
        response.raise_for_status()

    def upload_directory(
        self,
        parent_dir: str,
        directory: Path | str,
        compress_method: CompressMethod,
        mkdir: bool | None = None,
        zip_metadata_encoding: str | None = None,
    ) -> None:
        with _prepare_upload_directory(parent_dir, directory, compress_method, mkdir, zip_metadata_encoding) as (
            files,
            params,
        ):
            response = self.inner.post("/upload-directory", files=files, params=params)
            response.raise_for_status()

    def download_file(self, path: str, target: IOBase | str | Path) -> None:
        response = self.inner.post("/download-file", params={"path": path})
        response.raise_for_status()
        _finish_download(response, target)

    def download_directory(self, path: str, target_parent_directory: str | Path) -> Path:
        response = self.inner.post("/download-directory", params={"path": path})
        response.raise_for_status()
        return _finish_download_directory(response, path, target_parent_directory)

    def delete(self, path: str, recursive: bool | None = None) -> bool:
        params = _prepare_delete(path, recursive)
        response = self.inner.post("/delete", params=params)
        response.raise_for_status()
        return bool(response.text)

    def list_directory(self, directory: str) -> list[FileSystemInfo]:
        response = self.inner.post("/list-directory", params={"directory": directory})
        response.raise_for_status()
        return _finish_list_directory(response)

    def rename(self, path: str, new_name: str) -> None:
        response = self.inner.post("/rename", params={"path": path, "new_name": new_name})
        response.raise_for_status()
