import math
from collections import Counter
from typing import Dict, List, Any

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

def process_text(text: str, documents: List[List[str]]) -> List[Dict[str, Any]]:
    """
    Process text to calculate TF-IDF metrics.
    Returns a list of dictionaries with word, tf, and idf for each term.
    """
    # Flatten all documents to calculate overall TF
    all_tokens = [token for doc in documents for token in doc]
    
    # Calculate metrics
    tf = calculate_tf(all_tokens)
    df = calculate_df(documents)
    idf = calculate_idf(documents, df)
    
    # Create a list of dictionaries with word, tf, and idf
    results = [
        {"word": term, "tf": tf.get(term, 0), "idf": idf.get(term, 0)}
        for term in tf.keys()
    ]
    
    # Sort by decreasing idf, then by decreasing tf for ties
    results.sort(key=lambda x: (-x["idf"], -x["tf"]))
    
    # Return top 50 words (or all if less than 50)
    return results[:50] 