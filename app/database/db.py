from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
import os
from typing import Generator, AsyncGenerator

# Получение URL базы данных из переменных окружения или используем значение по умолчанию для разработки
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@db:5432/tfidf")
SYNC_SQLALCHEMY_DATABASE_URL = os.getenv("SYNC_DATABASE_URL", "postgresql://postgres:postgres@db:5432/tfidf")

# Создаем асинхронный и синхронный движки SQLAlchemy
async_engine = create_async_engine(SQLALCHEMY_DATABASE_URL, echo=False)
sync_engine = create_engine(SYNC_SQLALCHEMY_DATABASE_URL, echo=False)

# Создаем фабрики сессий
AsyncSessionLocal = sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)

# Функция для получения асинхронной сессии базы данных
async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    async_session = AsyncSessionLocal()
    try:
        yield async_session
    finally:
        await async_session.close()

# Функция для получения синхронной сессии базы данных
def get_db() -> Generator[SessionLocal, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Функция для создания всех таблиц в базе данных (используется при инициализации)
def create_tables():
    from app.database.models import Base
    Base.metadata.create_all(bind=sync_engine) 