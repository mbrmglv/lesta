import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import router
from app.database.db import get_async_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Функция жизненного цикла приложения FastAPI."""
    # Startup code: This runs before the application starts accepting requests
    # Initialize database (can be moved to Alembic migrations in production)
    from app.database.db import create_tables
    create_tables()
    
    yield
    
    # Shutdown code: This runs when the application is shutting down
    # Cleanup resources here if needed

# Create FastAPI app
app = FastAPI(
    title="TF-IDF Web Application",
    description="A web application for analyzing text files using TF-IDF",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True) 