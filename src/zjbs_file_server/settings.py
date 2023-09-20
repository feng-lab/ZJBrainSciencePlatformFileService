from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ZJBS_FILE_", env_file=".env", env_file_encoding="UTF-8")

    # 监听地址和端口
    LISTEN_ADDRESS: str = "0.0.0.0:3000"

    # 主目录
    HOME_DIR: Path = Path(__file__).parent.parent.parent / ".data"
    # 日志目录
    LOG_DIR: Path = HOME_DIR / "log"
    # 文件目录
    FILE_DIR: Path = HOME_DIR / "file"

    # 调试模式
    DEBUG_MODE: bool = False

    # 传递RequestID的header键
    REQUEST_ID_HEADER_KEY: str = "X-Request-ID"

    # 文件读写缓冲区大小
    BUFFER_SIZE: int = 1024 * 64


settings = Settings()
