from typing import Never

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.gzip import GZipMiddleware
from loguru import logger
from starlette.responses import RedirectResponse

from zjbs_file_server import api
from zjbs_file_server.error import raise_internal_server_error, raise_not_found
from zjbs_file_server.log import init_logger
from zjbs_file_server.settings import settings
from zjbs_file_server.type import MiddlewareCallNext

# 配置日志
init_logger()

# 配置服务器
app = FastAPI(title="Zhejiang Brain Science Platform File Service", description="之江实验室 Brain Science 平台文件服务")
app.add_middleware(GZipMiddleware, minimum_size=1024)


@app.middleware("http")
async def handle_request_id(request: Request, call_next: MiddlewareCallNext) -> Response:
    request_id = request.headers.get(settings.REQUEST_ID_HEADER_KEY, "")
    with logger.contextualize(request_id=request_id):
        response = await call_next(request)
        response.headers[settings.REQUEST_ID_HEADER_KEY] = request_id
        return response


app.include_router(api.router)


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
