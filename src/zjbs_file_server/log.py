import sys

from loguru import logger

from zjbs_file_server.settings import settings

LOG_FORMAT: str = "{time:YYYY-MM-DD HH:mm:ss.SSS}|{level}|{name}:{function}:{line}|{extra[request_id]}|{message}"


def init_logger():
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
