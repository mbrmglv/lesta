import math
import re
from collections import Counter
from typing import List, Dict, Any
import time

from app.services.parsing import normalize_text
from app.logger import get_logger

# Create logger for this module
logger = get_logger(__name__)

def calculate_tf(tokens: List[str]) -> Dict[str, int]:
    """
    Calculate Term Frequency for each token.
    Returns a dictionary with terms as keys and their frequencies as values.
    """
    return dict(Counter(tokens))

def calculate_df(documents: List[List[str]]) -> Dict[str, int]:
    """
    Calculate Document Frequency for each term.
    Returns a dictionary with terms as keys and the number of documents they appear in as values.
    """
    # For each term, count in how many documents it appears
    df_counter = Counter()
    for doc in documents:
        # Add each unique term in the document
        df_counter.update(set(doc))
    return dict(df_counter)

def calculate_idf(documents: List[List[str]], df: Dict[str, int]) -> Dict[str, float]:
    """
    Calculate Inverse Document Frequency for each term.
    Using the formula: log((|D| + 1) / (df(t) + 1)) + 1 for smoothing.
    """
    num_docs = len(documents)
    return {
        term: math.log((num_docs + 1) / (df_count + 1)) + 1
        for term, df_count in df.items()
    }

def process_text(text: str, documents: List[str]) -> List[Dict[str, Any]]:
    """
    Process text to calculate TF-IDF scores for each word.
    
    Args:
        text: The entire text content
        documents: List of document segments
        
    Returns:
        List of dictionaries with word, tf (term frequency) and idf (inverse document frequency).
        Returns at most 50 words with highest IDF scores.
    """
    start_time = time.time()
    logger.info("Starting TF-IDF processing", text_length=len(text), doc_count=len(documents))
    
    # Normalize and tokenize the full text
    normalized_text = normalize_text(text)
    
    # Count term frequencies in the entire text
    words = re.findall(r'\b\w+\b', normalized_text)
    word_counts = Counter(words)
    
    # Filter out words less than 3 characters
    word_counts = {word: count for word, count in word_counts.items() if len(word) >= 3}
    
    logger.debug("Word counts calculated", unique_words=len(word_counts))
    
    # Calculate document frequencies
    doc_freq = {}
    total_docs = len(documents)
    
    for doc in documents:
        # Normalize and tokenize document
        normalized_doc = normalize_text(doc)
        
        # Get unique words in this document
        doc_words = set(re.findall(r'\b\w+\b', normalized_doc))
        
        # Increment document frequency for each word
        for word in doc_words:
            if len(word) >= 3:  # Filter out short words
                doc_freq[word] = doc_freq.get(word, 0) + 1
    
    logger.debug("Document frequencies calculated", unique_words=len(doc_freq))
    
    # Calculate TF-IDF scores
    results = []
    for word, count in word_counts.items():
        if word in doc_freq:
            # TF = Term Frequency
            tf = count
            
            # IDF = log((N+1)/(df+1)) + 1 (smoothed IDF)
            idf = math.log((total_docs + 1) / (doc_freq[word] + 1)) + 1
            
            results.append({
                "word": word,
                "tf": tf,
                "idf": idf
            })
    
    # Sort by IDF (highest first)
    results.sort(key=lambda x: x["idf"], reverse=True)
    
    # Limit to top 50 results
    results = results[:50]
    
    processing_time = time.time() - start_time
    logger.info(
        "TF-IDF processing completed",
        processing_time=processing_time,
        results_count=len(results)
    )
    
    return results 