import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.orm.decl_api import DeclarativeMeta

# Create base class for SQLAlchemy models
Base: DeclarativeMeta = declarative_base()


class TextAnalysis(Base):
    """Model for storing information about the uploaded file and analysis results."""

    __tablename__ = "text_analyses"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(20), default="processing")  # processing, completed, failed
    error_message = Column(Text, nullable=True)

    # One-to-many relationship with WordResult
    words = relationship(
        "WordResult", back_populates="analysis", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<TextAnalysis(id='{self.id}', filename='{self.filename}', status='{self.status}')>"


class WordResult(Base):
    """Model for storing TF-IDF analysis results for each word."""

    __tablename__ = "word_results"

    id = Column(Integer, primary_key=True)
    analysis_id = Column(
        String(36), ForeignKey("text_analyses.id", ondelete="CASCADE"), nullable=False
    )
    word = Column(String(255), nullable=False)
    tf = Column(Integer, nullable=False)
    df = Column(
        Integer, nullable=False, default=1
    )  # Количество документов, содержащих слово
    idf = Column(Float, nullable=False)
    document_sources = Column(Text, nullable=True)  # Документы-источники со счетчиками

    # Many-to-one relationship with TextAnalysis
    analysis = relationship("TextAnalysis", back_populates="words")

    def __repr__(self):
        return f"<WordResult(word='{self.word}', tf={self.tf}, df={self.df}, idf={self.idf})>"
