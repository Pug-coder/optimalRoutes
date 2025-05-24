from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List, Any
import os
from pathlib import Path

from .config import Settings as AppSettings
from .config import (
    AppConfig, RunConfig, ApiPrefix, 
    DatabaseConfig, CorsConfig, LogConfig
)


class EnvSettings(BaseSettings):
    """
    Настройки приложения, загружаемые из переменных окружения.
    
    Префикс для всех переменных - "ROUTES_".
    Например, ROUTES_APP_DEBUG=true, ROUTES_DB_URL=postgresql://...
    """
    
    # Настройки приложения
    APP_NAME: Optional[str] = None
    APP_DEBUG: Optional[bool] = None
    APP_VERSION: Optional[str] = None
    
    # Настройки запуска
    RUN_HOST: Optional[str] = None
    RUN_PORT: Optional[int] = None
    
    # Настройки API
    API_PREFIX: Optional[str] = None
    
    # Настройки базы данных
    DB_URL: Optional[str] = None
    DB_POOL_SIZE: Optional[int] = None
    DB_ECHO: Optional[bool] = None
    
    # Настройки CORS
    CORS_ALLOW_ORIGINS: Optional[str] = None  # Список через запятую
    CORS_ALLOW_CREDENTIALS: Optional[bool] = None
    CORS_ALLOW_METHODS: Optional[str] = None  # Список через запятую
    CORS_ALLOW_HEADERS: Optional[str] = None  # Список через запятую
    
    # Настройки логирования
    LOG_LEVEL: Optional[str] = None
    LOG_FORMAT: Optional[str] = None
    
    model_config = SettingsConfigDict(
        env_prefix="ROUTES_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


def get_settings() -> AppSettings:
    """
    Загружает настройки из переменных окружения и объединяет 
    их с настройками по умолчанию.
    
    Returns:
        Настройки приложения с примененными переменными окружения
    """
    # Проверяем, есть ли в импортах тестовые настройки
    try:
        from test_config import test_settings
        # Если можем импортировать test_settings, используем их
        return test_settings
    except ImportError:
        # Если нет, загружаем из переменных окружения
        pass
        
    # Загружаем настройки из переменных окружения
    env_settings = EnvSettings()
    
    # Создаем объект конфигурации приложения
    app_config = AppConfig(
        app_name=env_settings.APP_NAME or AppConfig().app_name,
        debug=env_settings.APP_DEBUG 
            if env_settings.APP_DEBUG is not None else AppConfig().debug,
        version=env_settings.APP_VERSION or AppConfig().version
    )
    
    # Конфигурация запуска
    run_config = RunConfig(
        host=env_settings.RUN_HOST or RunConfig().host,
        port=env_settings.RUN_PORT or RunConfig().port
    )
    
    # Конфигурация API
    api_config = ApiPrefix(
        prefix=env_settings.API_PREFIX or ApiPrefix().prefix
    )
    
    # Проверяем, нужно ли использовать SQLite для тестирования
    db_url = env_settings.DB_URL
    if db_url and "sqlite" in db_url:
        # Для SQLite нужно использовать только URL без pool_size
        db_config = DatabaseConfig(
            url=db_url,
            echo=env_settings.DB_ECHO 
                if env_settings.DB_ECHO is not None else True
        )
    else:
        # Обычная конфигурация базы данных
        db_config = DatabaseConfig(
            url=db_url or DatabaseConfig().url,
            pool_size=env_settings.DB_POOL_SIZE or DatabaseConfig().pool_size,
            echo=env_settings.DB_ECHO 
                if env_settings.DB_ECHO is not None 
                else DatabaseConfig().echo
        )
    
    # Конфигурация CORS
    cors_config = CorsConfig(
        allow_origins=_parse_list(
            env_settings.CORS_ALLOW_ORIGINS, 
            CorsConfig().allow_origins
        ),
        allow_credentials=env_settings.CORS_ALLOW_CREDENTIALS 
            if env_settings.CORS_ALLOW_CREDENTIALS is not None 
            else CorsConfig().allow_credentials,
        allow_methods=_parse_list(
            env_settings.CORS_ALLOW_METHODS, 
            CorsConfig().allow_methods
        ),
        allow_headers=_parse_list(
            env_settings.CORS_ALLOW_HEADERS, 
            CorsConfig().allow_headers
        )
    )
    
    # Конфигурация логирования
    log_config = LogConfig(
        level=env_settings.LOG_LEVEL or LogConfig().level,
        format=env_settings.LOG_FORMAT or LogConfig().format
    )
    
    # Создаем и возвращаем общие настройки
    return AppSettings(
        app=app_config,
        run=run_config,
        api=api_config,
        db=db_config,
        cors=cors_config,
        log=log_config
    )


def _parse_list(value: Optional[str], default: List[Any]) -> List[Any]:
    """
    Парсит строку, разделенную запятыми, в список.
    
    Args:
        value: Строка со значениями, разделенными запятыми
        default: Значение по умолчанию, если строка пуста
        
    Returns:
        Список значений
    """
    if not value:
        return default
    
    # Разделяем строку по запятым и удаляем пробелы
    return [item.strip() for item in value.split(",") if item.strip()] 