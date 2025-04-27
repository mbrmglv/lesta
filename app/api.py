import os
import tempfile
from fastapi import APIRouter, UploadFile, File, HTTPException, Query, BackgroundTasks, Depends, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.parsing import split_into_documents
from app.services.tfidf import process_text
from app.schemas import UploadResponse, ResultsResponse, WordInfo, ErrorResponse
from app.database.db import get_async_db
from app.database import crud
from app.logger import get_logger, TimingLogger

# Create logger for this module
logger = get_logger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/", response_class=HTMLResponse, summary="Home Page", description="Renders the home page with file upload form")
async def home(request: Request):
    """Render the home page with file upload form."""
    logger.debug("Home page requested", client_host=request.client.host)
    return templates.TemplateResponse("index.html", {"request": request})

async def process_file_task(file_path: str, task_id: str, db: AsyncSession):
    """Background task to process the uploaded file."""
    logger_context = {"task_id": task_id, "file_path": file_path}
    logger.info("Starting file processing task", **logger_context)
    
    try:
        # Read the file
        with TimingLogger(logger, "file_reading", **logger_context):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read()
                    logger.debug("File read with utf-8 encoding", file_size=len(text), **logger_context)
            except UnicodeDecodeError:
                # Try with another encoding if utf-8 fails
                logger.warning("Failed to read with utf-8 encoding, trying cp1251", **logger_context)
                try:
                    with open(file_path, 'r', encoding='cp1251') as f:
                        text = f.read()
                        logger.debug("File read with cp1251 encoding", file_size=len(text), **logger_context)
                except Exception as e:
                    # Update analysis status to "failed" in case of an error
                    logger.error("Failed to read file", error=str(e), **logger_context)
                    await crud.update_text_analysis(db, task_id, "failed", str(e))
                    return

        try:
            # Process the text
            with TimingLogger(logger, "document_splitting", **logger_context):
                documents = split_into_documents(text)
                logger.debug("Text split into documents", doc_count=len(documents), **logger_context)

            with TimingLogger(logger, "tfidf_processing", **logger_context):
                results = process_text(text, documents)
                logger.debug("TF-IDF processing completed", results_count=len(results), **logger_context)
            
            # Save results to the database
            with TimingLogger(logger, "save_results", **logger_context):
                await crud.add_word_results(db, task_id, results)
                logger.info("Word results saved to database", count=len(results), **logger_context)
            
            # Update analysis status to "completed"
            await crud.update_text_analysis(db, task_id, "completed")
            logger.info("File processing completed successfully", **logger_context)
        except Exception as e:
            # Update analysis status to "failed" in case of an error
            logger.error("Processing failed", error=str(e), exc_info=True, **logger_context)
            await crud.update_text_analysis(db, task_id, "failed", str(e))
    finally:
        # Delete the temporary file
        try:
            os.unlink(file_path)
            logger.debug("Temporary file deleted", **logger_context)
        except OSError as e:
            logger.warning("Failed to delete temporary file", error=str(e), **logger_context)

@router.post(
    "/upload", 
    response_model=UploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload Text File",
    description="Upload a text file for TF-IDF analysis. The file will be processed asynchronously.",
    responses={
        202: {"description": "File accepted for processing", "model": UploadResponse},
        400: {"description": "Invalid request", "model": ErrorResponse},
        500: {"description": "Server error", "model": ErrorResponse}
    }
)
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Text file to analyze (.txt or .text format)"),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Upload a text file and process it in the background.
    Returns a task ID for retrieving results.
    
    - **file**: Text file (.txt or .text) with content to analyze
    
    The file size is limited to 5MB.
    """
    request_id = id(file)
    logger.info("File upload request received", 
               filename=file.filename, 
               content_type=file.content_type,
               request_id=request_id)
    
    # Validate file
    if not file.filename:
        logger.warning("Upload rejected: No filename provided", request_id=request_id)
        raise HTTPException(status_code=400, detail="No file provided")
    
    if not file.filename.endswith(('.txt', '.text')):
        logger.warning("Upload rejected: Invalid file type", 
                      filename=file.filename, 
                      request_id=request_id)
        raise HTTPException(status_code=400, detail="Only text files are allowed")
    
    # Create an analysis record in the database
    db_analysis = await crud.create_text_analysis(db, file.filename)
    task_id = db_analysis.id
    logger.info("Analysis task created", task_id=task_id, request_id=request_id)
    
    # Save the uploaded file to a temporary location
    with tempfile.NamedTemporaryFile(delete=False) as temp:
        content = await file.read()
        if len(content) > 5 * 1024 * 1024:  # 5MB limit
            logger.warning("Upload rejected: File too large", 
                          file_size=len(content), 
                          limit=5*1024*1024, 
                          task_id=task_id,
                          request_id=request_id)
            raise HTTPException(status_code=400, detail="File too large")
        
        temp.write(content)
        temp_path = temp.name
        logger.debug("File saved to temporary location", 
                    temp_path=temp_path, 
                    file_size=len(content),
                    task_id=task_id,
                    request_id=request_id)
    
    # Process the file in the background
    background_tasks.add_task(process_file_task, temp_path, task_id, db)
    logger.info("Background processing task scheduled", task_id=task_id, request_id=request_id)
    
    return UploadResponse(
        task_id=task_id,
        message="File upload successful. Processing started."
    )

@router.get(
    "/results/{task_id}", 
    response_model=ResultsResponse,
    summary="Get Analysis Results",
    description="Get the processed TF-IDF results for a specific task. Supports pagination.",
    responses={
        200: {"description": "Successful response with results", "model": ResultsResponse},
        202: {"description": "Analysis is still processing", "model": ErrorResponse},
        404: {"description": "Analysis not found", "model": ErrorResponse},
        500: {"description": "Analysis failed", "model": ErrorResponse}
    }
)
async def get_results(
    task_id: str, 
    page: int = Query(1, ge=1, description="Page number for pagination"),
    request: Request = None,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Get the processed results for a specific task.
    Supports pagination with 10 items per page.
    
    - **task_id**: UUID of the analysis task
    - **page**: Page number (starting from 1)
    
    If accessed from a browser, returns an HTML page with results.
    If accessed programmatically, returns JSON data.
    """
    logger.info("Results requested", task_id=task_id, page=page)
    
    # Get the analysis from the database
    with TimingLogger(logger, "get_analysis", task_id=task_id):
        analysis = await crud.get_text_analysis(db, task_id)
    
    if not analysis:
        logger.warning("Analysis not found", task_id=task_id)
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    if analysis.status == "processing":
        logger.info("Analysis still processing", task_id=task_id, status=analysis.status)
        raise HTTPException(status_code=202, detail="Analysis is still processing")
    
    if analysis.status == "failed":
        error_message = analysis.error_message or "An error occurred during processing"
        logger.warning("Analysis failed", task_id=task_id, error=error_message)
        raise HTTPException(status_code=500, detail=error_message)
    
    # Pagination
    items_per_page = 10
    skip = (page - 1) * items_per_page
    
    # Get the total number of results
    with TimingLogger(logger, "count_results", task_id=task_id):
        total_items = await crud.count_word_results(db, task_id)
    
    total_pages = (total_items + items_per_page - 1) // items_per_page
    logger.debug("Pagination info", 
                task_id=task_id, 
                page=page, 
                total_pages=total_pages, 
                total_items=total_items)
    
    # Adjust the page if it's out of range
    if page > total_pages and total_pages > 0:
        page = total_pages
        skip = (page - 1) * items_per_page
        logger.debug("Adjusted page number", task_id=task_id, adjusted_page=page)
    
    # Get words for the current page
    with TimingLogger(logger, "get_word_results", task_id=task_id, page=page):
        db_words = await crud.get_word_results(db, task_id, skip, items_per_page)
    
    # Convert to Pydantic models
    items = [WordInfo(word=word.word, tf=word.tf, idf=word.idf) for word in db_words]
    
    # Check Accept header to determine response format
    accept_header = request.headers.get("accept", "") if request else ""
    is_html_request = request and ("text/html" in accept_header or "*/*" in accept_header) and "application/json" not in accept_header
    
    logger.info("Returning results", 
               task_id=task_id, 
               format="html" if is_html_request else "json",
               items_count=len(items))
    
    # If this is a browser request and it accepts HTML, render a template
    if is_html_request:
        return templates.TemplateResponse(
            "results.html",
            {
                "request": request,
                "items": items,
                "task_id": task_id,
                "page": page,
                "total_pages": total_pages,
                "total_items": total_items
            }
        )
    
    # Otherwise return JSON
    return ResultsResponse(
        items=items,
        total=total_items,
        page=page,
        pages=total_pages
    )

@router.get(
    "/view/{task_id}", 
    response_class=HTMLResponse,
    summary="View Results Page",
    description="Render HTML page with results table for a specific analysis task.",
    responses={
        200: {"description": "HTML page with results"},
        202: {"description": "Analysis is still processing"},
        404: {"description": "Analysis not found"},
        500: {"description": "Analysis failed"}
    }
)
async def view_results(
    request: Request, 
    task_id: str, 
    page: int = Query(1, ge=1, description="Page number for pagination"),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Render HTML page with results table.
    
    - **task_id**: UUID of the analysis task
    - **page**: Page number (starting from 1)
    """
    logger.debug("View results page requested", task_id=task_id, page=page)
    return await get_results(task_id, page, request, db) 