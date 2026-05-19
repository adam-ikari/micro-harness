# tests/test_search.py
"""Tests for DuckDuckGo search."""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from spark.search.duckduckgo import DuckDuckGoSearch, SearchResult, SearchResponse


def test_search_result_dataclass():
    """Test SearchResult dataclass."""
    result = SearchResult(
        title="Test Title",
        url="https://example.com",
        snippet="Test snippet"
    )
    assert result.title == "Test Title"
    assert result.url == "https://example.com"
    assert result.snippet == "Test snippet"
    assert result.source == "duckduckgo"


def test_search_response_dataclass():
    """Test SearchResponse dataclass."""
    results = [
        SearchResult(title="Test", url="https://example.com", snippet="Snippet")
    ]
    response = SearchResponse(query="test", results=results)
    assert response.query == "test"
    assert len(response.results) == 1


def test_search_response_to_text():
    """Test SearchResponse to_text method."""
    results = [
        SearchResult(title="Test", url="https://example.com", snippet="Snippet")
    ]
    response = SearchResponse(query="python", results=results)
    text = response.to_text()
    assert "python" in text
    assert "Test" in text


def test_search_response_with_abstract():
    """Test SearchResponse with abstract."""
    results = []
    response = SearchResponse(
        query="what is python",
        results=results,
        abstract="Python is a programming language",
        source="Wikipedia"
    )
    text = response.to_text()
    assert "Python is a programming language" in text


def test_duckduckgo_init():
    """Test DuckDuckGoSearch initialization."""
    search = DuckDuckGoSearch()
    assert search.timeout == 10


def test_duckduckgo_init_custom_timeout():
    """Test DuckDuckGoSearch with custom timeout."""
    search = DuckDuckGoSearch(timeout=30)
    assert search.timeout == 30


@patch('spark.search.duckduckgo.urllib.request.urlopen')
def test_duckduckgo_search(mock_urlopen):
    """Test DuckDuckGo search."""
    mock_response = MagicMock()
    mock_data = {"Abstract": "Test abstract", "RelatedTopics": []}
    mock_response.read.return_value = json.dumps(mock_data).encode()
    mock_response.__enter__ = Mock(return_value=mock_response)
    mock_response.__exit__ = Mock(return_value=False)
    mock_urlopen.return_value = mock_response

    search = DuckDuckGoSearch()
    response = search.search("test query")

    assert response.query == "test query"


@patch('spark.search.duckduckgo.urllib.request.urlopen')
def test_duckduckgo_search_with_results(mock_urlopen):
    """Test DuckDuckGo search with results."""
    mock_response = MagicMock()
    mock_data = {
        "Abstract": "",
        "RelatedTopics": [
            {"Text": "Result 1", "FirstURL": "https://example.com/1"},
            {"Text": "Result 2", "FirstURL": "https://example.com/2"},
        ]
    }
    mock_response.read.return_value = json.dumps(mock_data).encode()
    mock_response.__enter__ = Mock(return_value=mock_response)
    mock_response.__exit__ = Mock(return_value=False)
    mock_urlopen.return_value = mock_response

    search = DuckDuckGoSearch()
    response = search.search("test")

    assert response.query == "test"


@patch('spark.search.duckduckgo.urllib.request.urlopen')
def test_duckduckgo_quick_search(mock_urlopen):
    """Test quick search."""
    mock_response = MagicMock()
    mock_data = {"Abstract": "Quick answer", "RelatedTopics": []}
    mock_response.read.return_value = json.dumps(mock_data).encode()
    mock_response.__enter__ = Mock(return_value=mock_response)
    mock_response.__exit__ = Mock(return_value=False)
    mock_urlopen.return_value = mock_response

    search = DuckDuckGoSearch()
    result = search.quick_search("test")

    assert result is not None


@patch('spark.search.duckduckgo.urllib.request.urlopen')
def test_duckduckgo_get_answer(mock_urlopen):
    """Test getting answer."""
    mock_response = MagicMock()
    mock_data = {"Abstract": "Direct answer here", "RelatedTopics": []}
    mock_response.read.return_value = json.dumps(mock_data).encode()
    mock_response.__enter__ = Mock(return_value=mock_response)
    mock_response.__exit__ = Mock(return_value=False)
    mock_urlopen.return_value = mock_response

    search = DuckDuckGoSearch()
    answer = search.get_answer("what is python")

    assert answer is not None