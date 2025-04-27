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

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/", response_class=HTMLResponse, summary="Home Page", description="Renders the home page with file upload form")
async def home(request: Request):
    """Render the home page with file upload form."""
    return templates.TemplateResponse("index.html", {"request": request})

async def process_file_task(file_path: str, task_id: str, db: AsyncSession):
    """Background task to process the uploaded file."""
    try:
        # Read the file
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
    except UnicodeDecodeError:
        # Try with another encoding if utf-8 fails
        try:
            with open(file_path, 'r', encoding='cp1251') as f:
                text = f.read()
        except Exception as e:
            # Обновляем статус анализа на "failed" в случае ошибки
            await crud.update_text_analysis(db, task_id, "failed", str(e))
            return

    try:
        # Process the text
        documents = split_into_documents(text)
        results = process_text(text, documents)
        
        # Сохраняем результаты в базу данных
        await crud.add_word_results(db, task_id, results)
        
        # Обновляем статус анализа на "completed"
        await crud.update_text_analysis(db, task_id, "completed")
    except Exception as e:
        # Обновляем статус анализа на "failed" в случае ошибки
        await crud.update_text_analysis(db, task_id, "failed", str(e))
    finally:
        # Удаляем временный файл
        try:
            os.unlink(file_path)
        except OSError as e:
            print(f"Warning: Failed to delete temporary file {file_path}: {e}")

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
    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    if not file.filename.endswith(('.txt', '.text')):
        raise HTTPException(status_code=400, detail="Only text files are allowed")
    
    # Создаем запись анализа в базе данных
    db_analysis = await crud.create_text_analysis(db, file.filename)
    task_id = db_analysis.id
    
    # Save the uploaded file to a temporary location
    with tempfile.NamedTemporaryFile(delete=False) as temp:
        content = await file.read()
        if len(content) > 5 * 1024 * 1024:  # 5MB limit
            raise HTTPException(status_code=400, detail="File too large")
        
        temp.write(content)
        temp_path = temp.name
    
    # Process the file in the background
    background_tasks.add_task(process_file_task, temp_path, task_id, db)
    
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
    # Получаем анализ из базы данных
    analysis = await crud.get_text_analysis(db, task_id)
    
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    if analysis.status == "processing":
        raise HTTPException(status_code=202, detail="Analysis is still processing")
    
    if analysis.status == "failed":
        error_message = analysis.error_message or "An error occurred during processing"
        raise HTTPException(status_code=500, detail=error_message)
    
    # Пагинация
    items_per_page = 10
    skip = (page - 1) * items_per_page
    
    # Получаем общее количество результатов
    total_items = await crud.count_word_results(db, task_id)
    total_pages = (total_items + items_per_page - 1) // items_per_page
    
    # Корректируем страницу, если она вне диапазона
    if page > total_pages and total_pages > 0:
        page = total_pages
        skip = (page - 1) * items_per_page
    
    # Получаем слова для текущей страницы
    db_words = await crud.get_word_results(db, task_id, skip, items_per_page)
    
    # Преобразуем в модели Pydantic
    items = [WordInfo(word=word.word, tf=word.tf, idf=word.idf) for word in db_words]
    
    # Проверяем заголовок Accept для определения формата ответа
    accept_header = request.headers.get("accept", "") if request else ""
    
    # Если это запрос из браузера и он принимает HTML, рендерим шаблон
    if request and ("text/html" in accept_header or "*/*" in accept_header) and "application/json" not in accept_header:
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
    
    # Иначе возвращаем JSON
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
    return await get_results(task_id, page, request, db) 