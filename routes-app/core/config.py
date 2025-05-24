from pydantic import BaseModel, Field, validator
from typing import Optional


class AppConfig(BaseModel):
    """Конфигурация приложения."""
    
    app_name: str = Field("Optimal Routes API", description="Название приложения")
    debug: bool = Field(False, description="Режим отладки")
    version: str = Field("0.1.0", description="Версия приложения")


class RunConfig(BaseModel):
    """Конфигурация запуска сервера."""
    
    host: str = Field("0.0.0.0", description="Хост для запуска сервера")
    port: int = Field(8000, description="Порт для запуска сервера", ge=1000, le=65535)
    
    @validator("port")
    def port_must_be_valid(cls, v):
        if not (1000 <= v <= 65535):
            raise ValueError("Port must be between 1000 and 65535")
        return v


class ApiPrefix(BaseModel):
    """Конфигурация префикса API."""
    
    prefix: str = Field("/api", description="Префикс API")
    
    @validator("prefix")
    def prefix_must_start_with_slash(cls, v):
        if not v.startswith("/"):
            return f"/{v}"
        return v


class DatabaseConfig(BaseModel):
    """Конфигурация базы данных."""
    
    url: str = Field(
        "postgresql+asyncpg://postgres:postgres@localhost:5432/optimroutes",
        description="URL подключения к базе данных"
    )
    pool_size: int = Field(5, description="Размер пула соединений", ge=1, le=20)
    echo: bool = Field(False, description="Вывод SQL запросов в консоль")
    
    @validator("url")
    def url_must_be_valid(cls, v):
        if not v.startswith(("postgresql+asyncpg://", "sqlite+aiosqlite://")):
            raise ValueError(
                "Database URL must start with postgresql+asyncpg:// or sqlite+aiosqlite://"
            )
        return v


class CorsConfig(BaseModel):
    """Конфигурация CORS."""
    
    allow_origins: list[str] = Field(
        ["*"], description="Разрешенные источники"
    )
    allow_credentials: bool = Field(
        True, description="Разрешить передачу учетных данных"
    )
    allow_methods: list[str] = Field(
        ["*"], description="Разрешенные методы"
    )
    allow_headers: list[str] = Field(
        ["*"], description="Разрешенные заголовки"
    )


class LogConfig(BaseModel):
    """Конфигурация логирования."""
    
    level: str = Field("INFO", description="Уровень логирования")
    format: str = Field(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Формат логов"
    )
    
    @validator("level")
    def level_must_be_valid(cls, v):
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v.upper()


class Settings(BaseModel):
    """Основные настройки приложения."""
    
    app: AppConfig = Field(default_factory=AppConfig)
    run: RunConfig = Field(default_factory=RunConfig)
    api: ApiPrefix = Field(default_factory=ApiPrefix)
    db: DatabaseConfig = Field(default_factory=DatabaseConfig)
    cors: CorsConfig = Field(default_factory=CorsConfig)
    log: LogConfig = Field(default_factory=LogConfig)


# Создаем экземпляр настроек с значениями по умолчанию
settings = Settings()
