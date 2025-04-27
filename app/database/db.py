import os
from typing import AsyncGenerator, Generator, Type

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from app.logger import get_logger

# Create logger for this module
logger = get_logger(__name__)

# Get database URL from environment variables or use default value for development
SQLALCHEMY_DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+asyncpg://postgres:postgres@db:5432/tfidf"
)
SYNC_SQLALCHEMY_DATABASE_URL = os.getenv(
    "SYNC_DATABASE_URL", "postgresql://postgres:postgres@db:5432/tfidf"
)

logger.info(
    "Initializing database connections",
    async_url=SQLALCHEMY_DATABASE_URL.replace("postgres:", "***:").replace("@", "***@"),
    sync_url=SYNC_SQLALCHEMY_DATABASE_URL.replace("postgres:", "***:").replace(
        "@", "***@"
    ),
)

# Create asynchronous and synchronous SQLAlchemy engines
async_engine = create_async_engine(SQLALCHEMY_DATABASE_URL, echo=False)
sync_engine = create_engine(SYNC_SQLALCHEMY_DATABASE_URL, echo=False)

# Create session factories
AsyncSessionLocal = sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)
SessionLocalType = Type[Session]


# Function to get an asynchronous database session
async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    async_session = AsyncSessionLocal()
    logger.debug("Created async database session")
    try:
        yield async_session
    finally:
        await async_session.close()
        logger.debug("Closed async database session")


# Function to get a synchronous database session
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    logger.debug("Created sync database session")
    try:
        yield db
    finally:
        db.close()
        logger.debug("Closed sync database session")


# Function to create all tables in the database (used during initialization)
def create_tables():
    from app.database.models import Base

    logger.info("Creating database tables")
    try:
        Base.metadata.create_all(bind=sync_engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error("Failed to create database tables", exc_info=e)
        raise
