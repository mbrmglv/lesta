import re
import nltk
from typing import List

# Download NLTK stopwords if not already downloaded
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords', quiet=True)

from nltk.corpus import stopwords

# Get stopwords for English and Russian
STOP_WORDS = set(stopwords.words('english') + stopwords.words('russian'))

def normalize_text(text: str) -> str:
    """Normalize text: lowercase and remove special characters."""
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

def split_into_documents(text: str, min_docs: int = 10) -> List[List[str]]:
    """
    Split text into quasi-documents by paragraphs.
    Returns a list of documents, where each document is a list of tokens.
    """
    # Split by double newlines (paragraphs)
    paragraphs = re.split(r'\n\n+', text)
    
    # Filter out empty paragraphs and tokenize each
    docs = [tokenize(p) for p in paragraphs if p.strip()]
    
    # Filter out empty docs
    docs = [doc for doc in docs if doc]
    
    # If we don't have enough documents, split them further
    if len(docs) < min_docs and len(docs) > 0:
        # Try to split by single newlines
        paragraphs = re.split(r'\n+', text)
        docs = [tokenize(p) for p in paragraphs if p.strip()]
        docs = [doc for doc in docs if doc]
        
    # If we still don't have enough documents, create artificial ones
    if len(docs) < min_docs and len(docs) > 0:
        all_tokens = tokenize(text)
        chunk_size = max(1, len(all_tokens) // min_docs)
        docs = [all_tokens[i:i+chunk_size] for i in range(0, len(all_tokens), chunk_size)]
    
    # If no documents were created (e.g., empty text), return at least one empty document
    if not docs:
        docs = [[]]
    
    return docs 