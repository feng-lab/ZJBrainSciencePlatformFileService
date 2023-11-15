from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ZJBS_FILE_", env_file=".env", env_file_encoding="UTF-8")

    # 日志目录
    LOG_DIR: Path = Path(__file__).parent.parent.parent / ".data" / "log"
    # 文件目录
    FILE_DIR: Path = Path(__file__).parent.parent.parent / ".data" / "file"
    # 临时文件目录
    TEMP_DIR: Path = Path(__file__).parent.parent.parent / ".data" / "temp"

    # 调试模式
    DEBUG_MODE: bool = False


settings = Settings()
