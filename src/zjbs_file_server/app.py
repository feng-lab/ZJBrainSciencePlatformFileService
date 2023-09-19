import sys

from fastapi import FastAPI, Request, Response
from fastapi.middleware.gzip import GZipMiddleware
from loguru import logger

from zjbs_file_server import api
from zjbs_file_server.settings import settings
from zjbs_file_server.type import MiddlewareCallNext

# 配置日志
logger.remove()
log_config = {
    "level": "INFO",
    "rotation": "1 day",
    "retention": "14 days",
    "encoding": "UTF-8",
    "enqueue": True,
    "format": "{time:YYYY-MM-DD HH:mm:ss.SSS}|{level}|{name}:{function}:{line}|{extra[request_id]}|{message}",
}
logger.add(settings.LOG_DIR / "app.log", **log_config)
logger.add(settings.LOG_DIR / "error.log", **(log_config | {"level": "ERROR", "backtrace": True}))
if settings.DEBUG_MODE:
    logger.add(sys.stderr, level="TRACE", backtrace=True, diagnose=True, enqueue=True, format=log_config["format"])

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


@app.get("/")
def index():
    return settings
