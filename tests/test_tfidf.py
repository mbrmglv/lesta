import math

from app.services.parsing import tokenize
from app.services.tfidf import (
    calculate_df,
    calculate_idf,
    calculate_tf,
    process_documents,
    process_text,
)


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


def test_process_documents():
    # Test with document dictionary
    documents = {"doc1.txt": "Apple orange apple banana.", "doc2.txt": "Apple grape."}

    results = process_documents(documents)

    # Check the structure of results
    assert isinstance(results, list)

    # Check that all results contain the required fields
    for item in results:
        assert "word" in item
        assert "tf" in item
        assert "df" in item
        assert "idf" in item
        assert "document_sources" in item


def test_calculate_tf():
    tokens = ["apple", "orange", "apple", "banana", "apple"]
    tf = calculate_tf(tokens)
    assert tf["apple"] == 3
    assert tf["orange"] == 1
    assert tf["banana"] == 1


def test_calculate_df():
    documents = [["apple", "orange"], ["apple", "banana"], ["grape", "apple"]]
    df = calculate_df(documents)
    assert df["apple"] == 3  # appears in all docs
    assert df["orange"] == 1
    assert df["banana"] == 1
    assert df["grape"] == 1


def test_calculate_idf():
    documents = [["apple", "orange"], ["apple", "banana"], ["grape", "apple"]]
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
    # Legacy function test
    text = "Apple orange apple banana. Apple grape."
    # Передаем строки вместо списков токенов
    documents = ["Apple orange apple banana.", "Apple grape."]

    results = process_text(text, documents)

    # Check the structure of results
    assert isinstance(results, list)

    # Check that all results contain the required fields
    for item in results:
        assert "word" in item
        assert "tf" in item
        assert "df" in item
        assert "idf" in item
        assert "document_sources" in item
