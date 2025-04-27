from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from app.api import router

@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI application lifecycle function."""
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
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    swagger_ui_parameters={"syntaxHighlight.theme": "obsidian"}
)

# Custom OpenAPI schema
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description + """
        
        ## Features
        
        - Upload text files for TF-IDF analysis
        - Process documents in the background
        - View and paginate through analysis results
        
        ## API Endpoints
        
        * `/upload` - Upload text files for processing
        * `/results/{task_id}` - Get analysis results
        * `/view/{task_id}` - View formatted results page
        """,
        routes=app.routes,
    )
    
    # Add server information
    openapi_schema["servers"] = [
        {"url": "/", "description": "Current server"},
    ]
    
    # Add authentication information if needed
    # openapi_schema["components"]["securitySchemes"] = {...}
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

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