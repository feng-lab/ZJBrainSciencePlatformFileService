from typing import BinaryIO

from httpx import AsyncClient

from .model import FileSystemInfo

client: AsyncClient | None = None


async def init_client(base_url: str, **kwargs) -> None:
    global client
    client = AsyncClient(base_url=base_url, **kwargs)
    await client.__aenter__()


async def close_client() -> None:
    global client
    await client.__aexit__()


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


async def upload_zip(
    directory: str,
    file: BinaryIO,
    filename: str,
    mkdir: bool | None = None,
    allow_overwrite: bool | None = None,
    zip_metadata_encoding: str | None = None,
) -> None:
    params = {"directory": directory}
    if mkdir is not None:
        params["mkdir"] = mkdir
    if allow_overwrite is not None:
        params["allow_overwrite"] = allow_overwrite
    if zip_metadata_encoding is not None:
        params["zip_metadata_encoding"] = zip_metadata_encoding
    files = {"file": (filename, file, "application/octet-stream")}

    response = await client.post("/UploadZip", files=files, params=params)
    response.raise_for_status()


async def download(path: str, target: BinaryIO) -> None:
    response = await client.post("/Download", params={"path": path})
    response.raise_for_status()

    target.write(response.content)


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
