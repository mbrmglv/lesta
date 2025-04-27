import os
import tempfile
import shutil
from fastapi import APIRouter, UploadFile, File, HTTPException, Query, BackgroundTasks, Depends, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.services.parsing import load_documents_from_directory
from app.services.tfidf import process_documents
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

async def process_files_task(temp_dir: str, task_id: str, db: AsyncSession):
    """Background task to process multiple uploaded files."""
    logger_context = {"task_id": task_id, "temp_dir": temp_dir}
    logger.info("Starting multi-file processing task", **logger_context)
    
    try:
        # Load documents from the temporary directory
        with TimingLogger(logger, "loading_documents", **logger_context):
            documents = load_documents_from_directory(temp_dir)
            logger.debug("Documents loaded", doc_count=len(documents), **logger_context)
            
            if not documents:
                logger.error("No valid documents found in upload", **logger_context)
                await crud.update_text_analysis(db, task_id, "failed", "No valid documents found in upload")
                return

        try:
            # Process the documents
            with TimingLogger(logger, "tfidf_processing", **logger_context):
                results = process_documents(documents)
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
        # Delete the temporary directory
        try:
            shutil.rmtree(temp_dir)
            logger.debug("Temporary directory deleted", **logger_context)
        except OSError as e:
            logger.warning("Failed to delete temporary directory", error=str(e), **logger_context)

# Keep the original function for backward compatibility
async def process_file_task(file_path: str, task_id: str, db: AsyncSession):
    """Background task to process a single uploaded file (legacy method)."""
    logger_context = {"task_id": task_id, "file_path": file_path}
    logger.info("Starting file processing task (legacy method)", **logger_context)
    
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

        # Create a temporary directory and copy the file there
        temp_dir = tempfile.mkdtemp()
        filename = os.path.basename(file_path)
        output_path = os.path.join(temp_dir, filename or "uploaded_file.txt")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(text)
            
        # Use the multi-file processing approach
        await process_files_task(temp_dir, task_id, db)
    finally:
        # Delete the temporary file
        try:
            os.unlink(file_path)
            logger.debug("Temporary file deleted", **logger_context)
        except OSError as e:
            logger.warning("Failed to delete temporary file", error=str(e), **logger_context)

# Add new endpoint for multiple file upload
@router.post(
    "/upload-multiple", 
    response_model=UploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload Multiple Text Files",
    description="Upload multiple text files for TF-IDF analysis. The files will be processed asynchronously.",
    responses={
        202: {"description": "Files accepted for processing", "model": UploadResponse},
        400: {"description": "Invalid request", "model": ErrorResponse},
        500: {"description": "Server error", "model": ErrorResponse}
    }
)
async def upload_multiple_files(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(..., description="Text files to analyze (.txt or .text format)"),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Upload multiple text files and process them in the background.
    Returns a task ID for retrieving results.
    
    - **files**: List of text files (.txt or .text) to analyze
    
    Each file size is limited to 5MB, and the total upload is limited to 20MB.
    """
    request_id = id(files)
    logger.info("Multiple files upload request received", 
               file_count=len(files), 
               request_id=request_id)
    
    # Validate files
    if not files or len(files) == 0:
        logger.warning("Upload rejected: No files provided", request_id=request_id)
        raise HTTPException(status_code=400, detail="No files provided")
    
    total_size = 0
    max_total_size = 20 * 1024 * 1024  # 20MB total limit
    
    # Create an analysis record in the database
    filenames = ", ".join([f.filename for f in files if f.filename])
    db_analysis = await crud.create_text_analysis(db, filenames)
    task_id = db_analysis.id
    logger.info("Analysis task created", task_id=task_id, request_id=request_id)
    
    # Create a temporary directory to store the files
    temp_dir = tempfile.mkdtemp()
    logger.debug("Temporary directory created", temp_dir=temp_dir, task_id=task_id)
    
    try:
        # Save all files to the temporary directory
        for i, file in enumerate(files):
            if not file.filename:
                continue
                
            if not file.filename.endswith(('.txt', '.text')):
                logger.warning("Skipping invalid file type", 
                              filename=file.filename, 
                              task_id=task_id)
                continue
                
            # Read file content
            content = await file.read()
            total_size += len(content)
            
            if total_size > max_total_size:
                logger.warning("Upload rejected: Total files too large", 
                              total_size=total_size, 
                              limit=max_total_size, 
                              task_id=task_id)
                raise HTTPException(status_code=400, detail="Total upload size too large")
            
            # Save to temporary file
            safe_filename = os.path.basename(file.filename)
            # Ensure unique filenames
            if os.path.exists(os.path.join(temp_dir, safe_filename)):
                safe_filename = f"{i}_{safe_filename}"
                
            file_path = os.path.join(temp_dir, safe_filename)
            with open(file_path, 'wb') as f:
                f.write(content)
                
            logger.debug("File saved", 
                        filename=safe_filename, 
                          file_size=len(content), 
                        task_id=task_id)
        
        # Process files in the background
        background_tasks.add_task(process_files_task, temp_dir, task_id, db)
        logger.info("Background processing task scheduled", task_id=task_id, request_id=request_id)
        
        return UploadResponse(
            task_id=task_id,
            message=f"Files upload successful. Processing started for {len(files)} files."
        )
    except Exception as e:
        # Clean up on error
        try:
            shutil.rmtree(temp_dir)
        except OSError:
            pass
        logger.error("Error processing upload", error=str(e), task_id=task_id, request_id=request_id)
        await crud.update_text_analysis(db, task_id, "failed", str(e))
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

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
    items = [WordInfo(
        word=word.word, 
        tf=word.tf, 
        df=word.df, 
        idf=word.idf,
        document_sources=word.document_sources or ""
    ) for word in db_words]
    
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

@router.get("/view/{task_id}")
async def view_results(
    request: Request,
    task_id: str,
    page: int = Query(1, ge=1),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Render a page with the TF-IDF analysis results for a specific task.
    """
    # Check if task exists and get its data
    task = await crud.get_text_analysis(db, task_id)
    if not task:
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "message": "Task not found"}
        )
    
    if task.status != "completed":
        return templates.TemplateResponse(
            "processing.html",
            {"request": request, "task_id": task_id, "status": task.status}
        )
    
    # Get results with pagination
    try:
        page_size = 10
        offset = (page - 1) * page_size
        
        # Count total items for pagination
        total_items = await crud.count_word_results(db, task_id)
        
        # If no results found
        if total_items == 0:
            return templates.TemplateResponse(
                "error.html",
                {"request": request, "message": "No results found for this task"}
            )
        
        # Calculate total pages
        total_pages = (total_items + page_size - 1) // page_size
        
        # Check if page number is valid
        if page > total_pages:
            return templates.TemplateResponse(
                "error.html",
                {"request": request, "message": f"Invalid page number. The task has only {total_pages} page(s)."}
            )
        
        # Get paginated results for this page
        results = await crud.get_word_results(db, task_id, offset, page_size)
        
        # Prepare results for template
        items = [WordInfo(
            word=result.word, 
            tf=result.tf, 
            df=result.df, 
            idf=result.idf,
            document_sources=result.document_sources or ""
        ) for result in results]
        
        return templates.TemplateResponse(
            "results.html",
            {
                "request": request,
                "task_id": task_id,
                "items": items,
                "page": page,
                "total_pages": total_pages,
                "total_items": total_items
            }
        )
    except Exception as e:
        logger.error(f"Error displaying results: {str(e)}")
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "message": f"Error displaying results: {str(e)}"}
        ) 