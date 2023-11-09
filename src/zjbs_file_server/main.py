import sys
from typing import Awaitable, Callable, Never

from fastapi import FastAPI, HTTPException
from fastapi.middleware.gzip import GZipMiddleware
from loguru import logger
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response

from zjbs_file_server.api import router as api_router
from zjbs_file_server.restful_api import router as restful_api_router
from zjbs_file_server.settings import settings
from zjbs_file_server.util import raise_internal_server_error, raise_not_found

# 配置日志
LOG_FORMAT: str = "{time:YYYY-MM-DD HH:mm:ss.SSS}|{level}|{name}:{function}:{line}|{extra[request_id]}|{message}"
logger.remove()
log_config = {
    "level": "INFO",
    "rotation": "1 day",
    "retention": "14 days",
    "encoding": "UTF-8",
    "enqueue": True,
    "format": LOG_FORMAT,
}
logger.add(settings.LOG_DIR / "app.log", **log_config)
logger.add(settings.LOG_DIR / "error.log", **(log_config | {"level": "ERROR", "backtrace": True}))
if settings.DEBUG_MODE:
    logger.add(sys.stderr, level="TRACE", backtrace=True, diagnose=True, enqueue=True, format=LOG_FORMAT)

# 配置服务器
app = FastAPI(title="Zhejiang Brain Science Platform File Service", description="之江实验室 Brain Science 平台文件服务")
app.add_middleware(GZipMiddleware, minimum_size=1024)


@app.middleware("http")
async def handle_request_id(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    request_id = request.headers.get(settings.REQUEST_ID_HEADER_KEY, "")
    with logger.contextualize(request_id=request_id):
        response = await call_next(request)
        response.headers[settings.REQUEST_ID_HEADER_KEY] = request_id
        return response


app.include_router(api_router)
app.include_router(restful_api_router)


@app.exception_handler(Exception)
async def handle_exception(request: Request, e: Exception) -> Never:
    if isinstance(e, HTTPException):
        raise
    logger.exception(f"unknown error, {request.url=}")
    raise_internal_server_error(str(e))


@app.get("/")
def index():
    if settings.DEBUG_MODE:
        return RedirectResponse(url="/docs")
    raise_not_found("page /")
