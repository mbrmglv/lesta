import pytest
import math
from app.services.parsing import tokenize, split_into_documents
from app.services.tfidf import calculate_tf, calculate_df, calculate_idf, process_text

def test_tokenize():
    # Simple test case
    text = "Hello, World! This is a test."
    tokens = tokenize(text)
    # Stopwords like "is", "a" should be removed
    assert "hello" in tokens
    assert "world" in tokens
    assert "test" in tokens
    assert "is" not in tokens
    assert "a" not in tokens
    
    # Special characters should be removed
    text_with_special = "Hello! @#$% 123 test."
    tokens = tokenize(text_with_special)
    assert "hello" in tokens
    assert "123" in tokens
    assert "test" in tokens
    assert "@" not in " ".join(tokens)

def test_split_into_documents():
    # Test with text containing paragraphs
    text = "This is a test paragraph.\n\nThis is a second paragraph."
    docs = split_into_documents(text)
    
    # We only check that we have at least one document and each document has tokens
    assert len(docs) > 0
    for doc in docs:
        assert isinstance(doc, list)
        # The document shouldn't be empty
        if doc:
            assert all(isinstance(token, str) for token in doc)

def test_calculate_tf():
    tokens = ["apple", "orange", "apple", "banana", "apple"]
    tf = calculate_tf(tokens)
    assert tf["apple"] == 3
    assert tf["orange"] == 1
    assert tf["banana"] == 1

def test_calculate_df():
    documents = [
        ["apple", "orange"],
        ["apple", "banana"],
        ["grape", "apple"]
    ]
    df = calculate_df(documents)
    assert df["apple"] == 3  # appears in all docs
    assert df["orange"] == 1
    assert df["banana"] == 1
    assert df["grape"] == 1

def test_calculate_idf():
    documents = [
        ["apple", "orange"],
        ["apple", "banana"],
        ["grape", "apple"]
    ]
    df = {"apple": 3, "orange": 1, "banana": 1, "grape": 1}
    idf = calculate_idf(documents, df)
    
    # IDF = log((N+1)/(df+1)) + 1
    # For apple: log((3+1)/(3+1)) + 1 = log(1) + 1 = 1
    # For orange: log((3+1)/(1+1)) + 1 = log(2) + 1 = ~1.693
    expected_apple_idf = 1.0
    expected_orange_idf = math.log(2) + 1
    
    assert round(idf["apple"], 5) == round(expected_apple_idf, 5)
    assert round(idf["orange"], 5) == round(expected_orange_idf, 5)

def test_process_text():
    text = "Apple orange apple banana. Apple grape."
    documents = [
        ["apple", "orange", "apple", "banana"],
        ["apple", "grape"]
    ]
    
    results = process_text(text, documents)
    
    # Check the structure of results
    assert isinstance(results, list)
    assert len(results) <= 50  # Should be at most 50 items
    
    # Check sorting: higher IDF values should come first
    if len(results) > 1:
        assert results[0]["idf"] >= results[1]["idf"]
    
    # Check that all results contain the required fields
    for item in results:
        assert "word" in item
        assert "tf" in item
        assert "idf" in item 