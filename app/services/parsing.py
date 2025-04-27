import re
import nltk
from typing import List
from nltk.corpus import stopwords

from app.logger import get_logger

# Create logger for this module
logger = get_logger(__name__)

# Download NLTK stopwords if not already downloaded
try:
    nltk.data.find('corpora/stopwords')
    logger.debug("NLTK stopwords already downloaded")
except LookupError:
    logger.info("Downloading NLTK stopwords")
    nltk.download('stopwords', quiet=True)
    logger.info("NLTK stopwords downloaded successfully")

# Get stopwords for English and Russian
STOP_WORDS = set(stopwords.words('english') + stopwords.words('russian'))
logger.debug(f"Loaded {len(STOP_WORDS)} stopwords for English and Russian")

def normalize_text(text: str) -> str:
    """Normalize text: lowercase and remove special characters."""
    logger.debug("Normalizing text", text_length=len(text))
    text = text.lower()
    text = re.sub(r'[^а-яa-z0-9\s]', ' ', text)
    return text

def tokenize(text: str) -> List[str]:
    """Split text into tokens and remove stopwords."""
    normalized_text = normalize_text(text)
    tokens = re.split(r'\s+', normalized_text)
    # Filter out empty strings and stopwords
    tokens = [token for token in tokens if token and token not in STOP_WORDS]
    return tokens

def split_into_documents(text: str, min_length: int = 100) -> List[str]:
    """
    Split text into documents by paragraphs or chunks.
    
    Args:
        text: The text to split
        min_length: Minimum document length
        
    Returns:
        List of document strings
    """
    logger.debug("Splitting text into documents", text_length=len(text))
    
    # First attempt to split by double newlines (paragraphs)
    paragraphs = re.split(r'\n\s*\n', text)
    paragraphs = [p.strip() for p in paragraphs if p.strip()]
    
    # If we have a reasonable number of paragraphs, use them as documents
    if len(paragraphs) >= 3:
        logger.info("Text split into paragraphs", count=len(paragraphs))
        return paragraphs
    
    # Otherwise split into chunks of approximately 500 chars
    logger.info("Not enough paragraphs, splitting into chunks")
    
    chunks = []
    current_chunk = ""
    
    for paragraph in paragraphs:
        if len(current_chunk) + len(paragraph) < 500:
            current_chunk += " " + paragraph if current_chunk else paragraph
        else:
            if current_chunk and len(current_chunk) >= min_length:
                chunks.append(current_chunk)
            current_chunk = paragraph
    
    # Add the last chunk if it's not empty and meets minimum length
    if current_chunk and len(current_chunk) >= min_length:
        chunks.append(current_chunk)
    
    # If we still don't have enough chunks, split the text into equal parts
    if len(chunks) < 3:
        logger.info("Not enough chunks, splitting into equal parts")
        total_length = len(text)
        chunk_size = max(min_length, total_length // 5)  # Aim for at least 5 chunks
        
        chunks = []
        for i in range(0, total_length, chunk_size):
            chunk = text[i:i + chunk_size]
            if len(chunk) >= min_length:
                chunks.append(chunk)
    
    logger.info("Text split into chunks", count=len(chunks))
    return chunks 