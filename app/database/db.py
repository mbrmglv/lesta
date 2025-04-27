from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
import os
from typing import Generator, AsyncGenerator

# Get database URL from environment variables or use default value for development
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@db:5432/tfidf")
SYNC_SQLALCHEMY_DATABASE_URL = os.getenv("SYNC_DATABASE_URL", "postgresql://postgres:postgres@db:5432/tfidf")

# Create asynchronous and synchronous SQLAlchemy engines
async_engine = create_async_engine(SQLALCHEMY_DATABASE_URL, echo=False)
sync_engine = create_engine(SYNC_SQLALCHEMY_DATABASE_URL, echo=False)

# Create session factories
AsyncSessionLocal = sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)

# Function to get an asynchronous database session
async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    async_session = AsyncSessionLocal()
    try:
        yield async_session
    finally:
        await async_session.close()

# Function to get a synchronous database session
def get_db() -> Generator[SessionLocal, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Function to create all tables in the database (used during initialization)
def create_tables():
    from app.database.models import Base
    Base.metadata.create_all(bind=sync_engine) 