from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, desc, func
from typing import List, Dict, Any, Optional

from app.database.models import TextAnalysis, WordResult

async def create_text_analysis(db: AsyncSession, filename: Optional[str] = None) -> TextAnalysis:
    """Creates a new text analysis record in the database."""
    db_analysis = TextAnalysis(filename=filename)
    db.add(db_analysis)
    await db.commit()
    await db.refresh(db_analysis)
    return db_analysis

async def get_text_analysis(db: AsyncSession, analysis_id: str) -> Optional[TextAnalysis]:
    """Gets a text analysis record by id."""
    result = await db.execute(
        select(TextAnalysis).where(TextAnalysis.id == analysis_id)
    )
    return result.scalars().first()

async def update_text_analysis(db: AsyncSession, analysis_id: str, status: str, error_message: Optional[str] = None) -> bool:
    """Updates the status of a text analysis."""
    stmt = update(TextAnalysis).where(TextAnalysis.id == analysis_id).values(
        status=status,
        error_message=error_message
    )
    await db.execute(stmt)
    await db.commit()
    return True

async def add_word_results(db: AsyncSession, analysis_id: str, word_results: List[Dict[str, Any]]) -> bool:
    """Adds word analysis results for a given text analysis."""
    for result in word_results:
        db_word_result = WordResult(
            analysis_id=analysis_id,
            word=result["word"],
            tf=result["tf"],
            idf=result["idf"]
        )
        db.add(db_word_result)
    
    await db.commit()
    return True

async def get_word_results(db: AsyncSession, analysis_id: str, skip: int = 0, limit: int = 10) -> List[WordResult]:
    """Gets word analysis results for a given text analysis with pagination."""
    result = await db.execute(
        select(WordResult)
        .where(WordResult.analysis_id == analysis_id)
        .order_by(desc(WordResult.idf), desc(WordResult.tf))
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()

async def count_word_results(db: AsyncSession, analysis_id: str) -> int:
    """Counts the total number of words for a given text analysis."""
    result = await db.execute(
        select(func.count())
        .where(WordResult.analysis_id == analysis_id)
    )
    return result.scalar() or 0 