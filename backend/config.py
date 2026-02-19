"""
配置文件
SQLite 数据库 + 本地文件存储（CSV和模型文件）
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


class Settings(BaseSettings):
    debug: bool = True

    # SQLite 数据库路径
    database_url: str = f"sqlite:///{Path(__file__).parent / 'storage' / 'tennis_coach.db'}"

    # 文件存储目录（CSV 和模型文件仍用文件系统）
    data_dir: str = str(Path(__file__).parent / "storage")

    allowed_origins: list[str] = [
        "http://localhost:8501",
        "http://localhost:3000",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )


settings = Settings()
