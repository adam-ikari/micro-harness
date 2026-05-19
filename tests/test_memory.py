# tests/test_memory.py
"""Tests for memory manager."""

import pytest
import tempfile
from pathlib import Path
from spark.memory.manager import MemoryManager


def test_memory_manager_init():
    """Test memory manager initialization."""
    with tempfile.TemporaryDirectory() as d:
        memory_path = Path(d) / "memory.md"
        manager = MemoryManager(memory_path=str(memory_path))
        assert manager.memory_path == memory_path


def test_memory_manager_creates_file():
    """Test memory manager creates file if not exists."""
    with tempfile.TemporaryDirectory() as d:
        memory_path = Path(d) / "memory.md"
        manager = MemoryManager(memory_path=str(memory_path))
        assert memory_path.exists()


def test_memory_manager_load_index():
    """Test loading index section."""
    with tempfile.TemporaryDirectory() as d:
        memory_path = Path(d) / "memory.md"
        manager = MemoryManager(memory_path=str(memory_path))

        index = manager.load_index()
        assert "Index" in index or "Empty" in index


def test_memory_manager_load_summary():
    """Test loading summary section."""
    with tempfile.TemporaryDirectory() as d:
        memory_path = Path(d) / "memory.md"
        manager = MemoryManager(memory_path=str(memory_path))

        summary = manager.load_summary()
        assert summary is not None


def test_memory_manager_load_details():
    """Test loading details section."""
    with tempfile.TemporaryDirectory() as d:
        memory_path = Path(d) / "memory.md"
        manager = MemoryManager(memory_path=str(memory_path))

        details = manager.load_details()
        assert details is not None


def test_memory_manager_append_to_index():
    """Test appending to index."""
    with tempfile.TemporaryDirectory() as d:
        memory_path = Path(d) / "memory.md"
        manager = MemoryManager(memory_path=str(memory_path))

        manager.append_to_index("Test fact: Python is great")

        content = memory_path.read_text()
        assert "Python is great" in content


def test_memory_manager_append_to_summary():
    """Test appending to summary."""
    with tempfile.TemporaryDirectory() as d:
        memory_path = Path(d) / "memory.md"
        manager = MemoryManager(memory_path=str(memory_path))

        manager.append_to_summary("Session summary test")

        content = memory_path.read_text()
        assert "Session summary test" in content


def test_memory_manager_append_to_details():
    """Test appending to details."""
    with tempfile.TemporaryDirectory() as d:
        memory_path = Path(d) / "memory.md"
        manager = MemoryManager(memory_path=str(memory_path))

        detail_id = manager.append_to_details("Detail content here")

        content = memory_path.read_text()
        assert "Detail content here" in content


def test_memory_manager_get_context():
    """Test getting context for LLM."""
    with tempfile.TemporaryDirectory() as d:
        memory_path = Path(d) / "memory.md"
        manager = MemoryManager(memory_path=str(memory_path))

        manager.append_to_index("Important fact")
        context = manager.get_context_for_llm()

        assert context is not None


def test_memory_manager_get_relevant_context():
    """Test getting relevant context."""
    with tempfile.TemporaryDirectory() as d:
        memory_path = Path(d) / "memory.md"
        manager = MemoryManager(memory_path=str(memory_path))

        manager.append_to_index("Python programming language")
        context = manager.get_relevant_context("What is Python?")

        assert context is not None


def test_memory_manager_get_keywords():
    """Test getting keywords."""
    with tempfile.TemporaryDirectory() as d:
        memory_path = Path(d) / "memory.md"
        manager = MemoryManager(memory_path=str(memory_path))

        manager.append_to_index("Python is a programming language")
        keywords = manager.get_keywords()

        assert isinstance(keywords, list)


def test_memory_manager_save_session():
    """Test saving session."""
    with tempfile.TemporaryDirectory() as d:
        memory_path = Path(d) / "memory.md"
        manager = MemoryManager(memory_path=str(memory_path))

        manager.save_session("Test session summary", ["fact1", "fact2"])

        content = memory_path.read_text()
        assert "Test session summary" in content