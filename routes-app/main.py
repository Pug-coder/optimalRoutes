import uvicorn
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from api import router as api_router
from core.settings import get_settings
from core.database import Base, engine  # noqa: F401

# Импортируем все модели, чтобы Alembic мог их обнаружить
from api.models import (  # noqa: F401
    Depot, Courier, Order, RoutePoint, Route, Location
)

# Получаем настройки
settings = get_settings()

# Настраиваем логирование
logging.basicConfig(
    level=getattr(logging, settings.log.level),
    format=settings.log.format
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Контекстный менеджер для управления жизненным циклом приложения.
    """
    # Выполняется при запуске приложения
    logger.info(f"Application {settings.app.app_name} v{settings.app.version} is starting")
    
    # Создаем таблицы если это тестовый запуск с SQLite
    # (в production будем использовать миграции Alembic)
    if settings.app.debug and 'sqlite' in settings.db.url:
        logger.info("SQLite detected in debug mode, creating database tables...")
        from sqlalchemy.schema import CreateTable
        
        async with engine.begin() as conn:
            # Проверяем, что таблицы нужно создать
            try:
                # Создаем все таблицы
                await conn.run_sync(Base.metadata.create_all)
                logger.info("Database tables created successfully")
            except Exception as e:
                logger.error(f"Error creating database tables: {e}")
    
    yield  # Здесь приложение работает
    
    # Выполняется при остановке приложения
    logger.info(f"Application {settings.app.app_name} is shutting down")


# Создаем экземпляр FastAPI
app = FastAPI(
    title=settings.app.app_name,
    version=settings.app.version,
    description="API для сервиса оптимальных маршрутов доставки",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    debug=settings.app.debug,
    lifespan=lifespan
)

# Добавляем CORS-поддержку
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors.allow_origins,
    allow_credentials=settings.cors.allow_credentials,
    allow_methods=settings.cors.allow_methods,
    allow_headers=settings.cors.allow_headers,
)


# Обработчик ошибок валидации
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Обработчик ошибок валидации запросов."""
    errors = []
    for error in exc.errors():
        field_path = ".".join(str(loc) for loc in error["loc"] if loc != "body")
        error_msg = {
            "field": field_path,
            "message": error["msg"],
            "type": error["type"]
        }
        errors.append(error_msg)
    
    logger.warning(f"Validation error: {errors}")
    
    return JSONResponse(
        status_code=422,
        content={"detail": "Validation error", "errors": errors}
    )


# Обработчик ошибок валидации Pydantic
@app.exception_handler(ValidationError)
async def pydantic_validation_exception_handler(request: Request, exc: ValidationError):
    """Обработчик ошибок валидации Pydantic моделей."""
    errors = []
    for error in exc.errors():
        field_path = ".".join(str(loc) for loc in error["loc"])
        error_msg = {
            "field": field_path,
            "message": error["msg"],
            "type": error["type"]
        }
        errors.append(error_msg)
    
    logger.warning(f"Pydantic validation error: {errors}")
    
    return JSONResponse(
        status_code=422,
        content={"detail": "Validation error", "errors": errors}
    )


# Добавляем обработчик неожиданных исключений
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Обработчик неожиданных исключений."""
    logger.exception(f"Unexpected error: {exc}")
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "message": str(exc) if settings.app.debug else "An unexpected error occurred"
        }
    )


# Подключаем API роутеры
app.include_router(
    api_router,
    prefix=settings.api.prefix
)


# Запуск приложения
if __name__ == "__main__":
    logger.info(f"Starting server at {settings.run.host}:{settings.run.port}")
    uvicorn.run(
        "main:app",
        host=settings.run.host,
        port=settings.run.port,
        reload=settings.app.debug,
    )
