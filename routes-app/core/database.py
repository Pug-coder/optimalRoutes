from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.engine.url import make_url
from sqlalchemy.pool import NullPool
import logging

from .settings import get_settings

# Получаем настройки приложения
settings = get_settings()

# Создаем базовый класс для моделей
Base = declarative_base()

# Настраиваем логгер для SQL-запросов
logger = logging.getLogger("sqlalchemy")
logger.setLevel(logging.DEBUG if settings.db.echo else logging.INFO)

# Создаем URL подключения к базе данных
db_url = make_url(settings.db.url)

# Настройки для создания движка базы данных
engine_kwargs = {
    "echo": settings.db.echo,
    "pool_pre_ping": True,
}

# Добавляем pool_size только для PostgreSQL, для SQLite не используем
if not db_url.drivername.startswith("sqlite"):
    engine_kwargs["pool_size"] = getattr(settings.db, "pool_size", 5)

# Если используется SQLite, отключаем пулинг соединений
if db_url.drivername.startswith("sqlite"):
    engine_kwargs["poolclass"] = NullPool
    # Для SQLite также добавляем параметр check_same_thread=False
    engine_kwargs["connect_args"] = {"check_same_thread": False}

# Создаем движок базы данных
engine = create_async_engine(settings.db.url, **engine_kwargs)

# Создаем фабрику сессий
SessionLocal = sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

async def get_db() -> AsyncSession:
    """
    Генератор сессий базы данных.
    
    Yields:
        Сессия базы данных.
    """
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close() 