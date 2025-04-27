from sqlalchemy import Column, Integer, String, Float, ForeignKey, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()

class TextAnalysis(Base):
    """Модель для хранения информации о загруженном файле и результатах анализа."""
    __tablename__ = "text_analyses"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(20), default="processing")  # processing, completed, failed
    error_message = Column(Text, nullable=True)
    
    # Связь один-ко-многим с WordResult
    words = relationship("WordResult", back_populates="analysis", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<TextAnalysis(id='{self.id}', filename='{self.filename}', status='{self.status}')>"

class WordResult(Base):
    """Модель для хранения результатов TF-IDF анализа для каждого слова."""
    __tablename__ = "word_results"
    
    id = Column(Integer, primary_key=True)
    analysis_id = Column(String(36), ForeignKey("text_analyses.id", ondelete="CASCADE"), nullable=False)
    word = Column(String(255), nullable=False)
    tf = Column(Integer, nullable=False)
    idf = Column(Float, nullable=False)
    
    # Связь многие-к-одному с TextAnalysis
    analysis = relationship("TextAnalysis", back_populates="words")
    
    def __repr__(self):
        return f"<WordResult(word='{self.word}', tf={self.tf}, idf={self.idf})>" 