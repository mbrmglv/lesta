from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, desc, func
from typing import List, Dict, Any, Optional

from app.database.models import TextAnalysis, WordResult
from app.logger import get_logger, TimingLogger

# Create logger for this module
logger = get_logger(__name__)

async def create_text_analysis(db: AsyncSession, filename: Optional[str] = None) -> TextAnalysis:
    """Creates a new text analysis record in the database."""
    logger.debug("Creating new text analysis", filename=filename)
    db_analysis = TextAnalysis(filename=filename)
    db.add(db_analysis)
    await db.commit()
    await db.refresh(db_analysis)
    logger.info("Created text analysis", analysis_id=db_analysis.id, filename=filename)
    return db_analysis

async def get_text_analysis(db: AsyncSession, analysis_id: str) -> Optional[TextAnalysis]:
    """Gets a text analysis record by id."""
    logger.debug("Getting text analysis", analysis_id=analysis_id)
    result = await db.execute(
        select(TextAnalysis).where(TextAnalysis.id == analysis_id)
    )
    analysis = result.scalars().first()
    if analysis:
        logger.debug("Text analysis found", analysis_id=analysis_id, status=analysis.status)
    else:
        logger.warning("Text analysis not found", analysis_id=analysis_id)
    return analysis

async def update_text_analysis(db: AsyncSession, analysis_id: str, status: str, error_message: Optional[str] = None) -> bool:
    """Updates the status of a text analysis."""
    logger.debug("Updating text analysis", analysis_id=analysis_id, status=status, has_error=error_message is not None)
    stmt = update(TextAnalysis).where(TextAnalysis.id == analysis_id).values(
        status=status,
        error_message=error_message
    )
    await db.execute(stmt)
    await db.commit()
    logger.info("Text analysis updated", analysis_id=analysis_id, status=status)
    return True

async def add_word_results(db: AsyncSession, analysis_id: str, word_results: List[Dict[str, Any]]) -> bool:
    """Adds word analysis results for a given text analysis."""
    with TimingLogger(logger, "add_word_results", analysis_id=analysis_id, count=len(word_results)):
        for result in word_results:
            db_word_result = WordResult(
                analysis_id=analysis_id,
                word=result["word"],
                tf=result["tf"],
                idf=result["idf"]
            )
            db.add(db_word_result)
        
        await db.commit()
        logger.info("Word results added to database", analysis_id=analysis_id, count=len(word_results))
    return True

async def get_word_results(db: AsyncSession, analysis_id: str, skip: int = 0, limit: int = 10) -> List[WordResult]:
    """Gets word analysis results for a given text analysis with pagination."""
    logger.debug("Getting word results", analysis_id=analysis_id, skip=skip, limit=limit)
    result = await db.execute(
        select(WordResult)
        .where(WordResult.analysis_id == analysis_id)
        .order_by(desc(WordResult.idf), desc(WordResult.tf))
        .offset(skip)
        .limit(limit)
    )
    word_results = result.scalars().all()
    logger.debug("Retrieved word results", analysis_id=analysis_id, count=len(word_results))
    return word_results

async def count_word_results(db: AsyncSession, analysis_id: str) -> int:
    """Counts the total number of words for a given text analysis."""
    logger.debug("Counting word results", analysis_id=analysis_id)
    result = await db.execute(
        select(func.count())
        .where(WordResult.analysis_id == analysis_id)
    )
    count = result.scalar() or 0
    logger.debug("Word result count", analysis_id=analysis_id, count=count)
    return count 