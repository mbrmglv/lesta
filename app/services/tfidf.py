import math
import re
import time
from collections import Counter, defaultdict
from typing import Any, DefaultDict, Dict, List

from app.logger import get_logger
from app.services.parsing import normalize_text

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
    df_counter: Counter[str] = Counter()
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


def process_documents(documents: Dict[str, str]) -> List[Dict[str, Any]]:
    """
    Process multiple documents to calculate TF-IDF scores for each word.

    Args:
        documents: Dictionary mapping document names to their content

    Returns:
        List of dictionaries with word, tf (term frequency), idf (inverse document frequency),
        and document_sources (mapping of documents to term frequency in each document).
        Returns at most words with highest IDF scores.
    """
    start_time = time.time()
    logger.info(
        "Starting TF-IDF processing for multiple documents", doc_count=len(documents)
    )

    if not documents:
        logger.warning("No documents provided for TF-IDF analysis")
        return []

    # Combine all documents for overall term frequency
    all_text = " ".join(documents.values())
    normalized_all_text = normalize_text(all_text)

    # Count term frequencies in the entire text
    words = re.findall(r"\b\w+\b", normalized_all_text)
    word_counts_counter = Counter(words)
    word_counts = dict(word_counts_counter)

    # Filter out words less than 3 characters
    word_counts = {word: count for word, count in word_counts.items() if len(word) >= 3}

    logger.debug("Word counts calculated", unique_words=len(word_counts))

    # Calculate document frequencies and track which words appear in which documents
    doc_freq: Dict[str, int] = {}
    word_doc_mapping: DefaultDict[str, Dict[str, int]] = defaultdict(
        dict
    )  # word -> {doc_name -> count in doc}
    total_docs = len(documents)

    for doc_name, content in documents.items():
        # Normalize document
        normalized_doc = normalize_text(content)

        # Count words in this document
        doc_words = re.findall(r"\b\w+\b", normalized_doc)
        doc_word_counts_counter = Counter(doc_words)
        doc_word_counts = dict(doc_word_counts_counter)

        # For each word in the document
        for word, count in doc_word_counts.items():
            if len(word) >= 3:  # Filter out short words
                # Update document frequency
                doc_freq[word] = doc_freq.get(word, 0) + 1

                # Store word count in this specific document
                word_doc_mapping[word][doc_name] = count

    logger.debug("Document frequencies calculated", unique_words=len(doc_freq))

    # Calculate TF-IDF scores
    results = []
    for word, count in word_counts.items():
        if word in doc_freq:
            # TF = Term Frequency
            tf = count

            # IDF = log((N+1)/(df+1)) + 1 (smoothed IDF)
            idf = math.log((total_docs + 1) / (doc_freq[word] + 1)) + 1

            # Get documents where this word appears with their counts
            doc_sources = word_doc_mapping[word]

            # Format document sources for better readability
            doc_sources_formatted = ", ".join(
                [f"{doc}({count})" for doc, count in doc_sources.items()]
            )

            results.append(
                {
                    "word": word,
                    "tf": tf,
                    "idf": idf,
                    "df": doc_freq[word],  # Add document frequency
                    "document_sources": doc_sources_formatted,
                }
            )

    # Sort by IDF (highest first)
    results.sort(key=lambda x: x["idf"], reverse=True)

    processing_time = time.time() - start_time
    logger.info(
        "TF-IDF processing completed",
        processing_time=processing_time,
        results_count=len(results),
    )

    return results


# Keep original function for backward compatibility, but redirect to new implementation
def process_text(text: str, documents: List[str]) -> List[Dict[str, Any]]:
    """
    Legacy function for processing a single text with pre-split documents.
    Now redirects to the new document-oriented approach.
    """
    logger.info(
        "Using legacy process_text function - converting to document dictionary"
    )
    doc_dict = {}
    for i, doc in enumerate(documents):
        doc_dict[f"document_{i+1}"] = doc

    # If original text isn't in documents, add it as a separate document
    if text not in documents:
        doc_dict["full_text"] = text

    return process_documents(doc_dict)
