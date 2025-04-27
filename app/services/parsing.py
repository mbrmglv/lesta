import re
import nltk
import os
from typing import List, Dict
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

def load_documents_from_directory(directory_path: str) -> Dict[str, str]:
    """
    Load multiple documents from a directory.
    
    Args:
        directory_path: Path to the directory containing text files
        
    Returns:
        Dictionary mapping filenames to their text content
    """
    logger.info(f"Loading documents from directory: {directory_path}")
    documents = {}
    
    try:
        for filename in os.listdir(directory_path):
            file_path = os.path.join(directory_path, filename)
            
            # Only process text files
            if os.path.isfile(file_path) and filename.endswith(('.txt', '.md')):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        documents[filename] = content
                        logger.debug(f"Loaded document: {filename}", length=len(content))
                except UnicodeDecodeError:
                    # Try a different encoding if utf-8 fails
                    try:
                        with open(file_path, 'r', encoding='cp1251') as f:
                            content = f.read()
                            documents[filename] = content
                            logger.debug(f"Loaded document with cp1251 encoding: {filename}", length=len(content))
                    except Exception as e:
                        logger.error(f"Failed to read file {filename}: {str(e)}")
    
        logger.info(f"Loaded {len(documents)} documents from {directory_path}")
        return documents
    except Exception as e:
        logger.error(f"Error loading documents from directory: {str(e)}")
        return {} 