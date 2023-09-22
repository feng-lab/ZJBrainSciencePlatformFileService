from typing import Never

from fastapi import HTTPException
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND, HTTP_500_INTERNAL_SERVER_ERROR


def raise_not_found(entity: str) -> Never:
    raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=f"{entity} not found")


def raise_bad_request(message: str) -> Never:
    raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=message)


def raise_internal_server_error(message: str) -> Never:
    raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=message)
