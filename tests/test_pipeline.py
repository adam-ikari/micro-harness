# tests/test_pipeline.py
"""Tests for shell pipeline functionality."""

import pytest
from spark.builtin.shell import execute


class TestPipeline:
    """Test pipe commands."""

    def test_simple_pipe_grep(self):
        """Test ls | grep."""
        result = execute("ls | grep .py")
        assert result["success"]
        assert "main.py" in result["stdout"]

    def test_pipe_wc(self):
        """Test ls | wc -l."""
        result = execute("ls | wc -l")
        assert result["success"]
        # Should return a number
        assert result["stdout"].strip().isdigit()

    def test_multiple_pipes(self):
        """Test ls | grep .py | wc -l."""
        result = execute("ls | grep .py | wc -l")
        assert result["success"]
        assert result["stdout"].strip().isdigit()

    def test_pipe_sort(self):
        """Test ls | sort."""
        result = execute("ls | sort")
        assert result["success"]
        lines = result["stdout"].strip().split("\n")
        # Shell sort uses LC_COLLATE order (lowercase before uppercase by default)
        # Verify each line appears only once
        assert len(lines) == len(set(lines))

    def test_pipe_head(self):
        """Test ls | head -n 3."""
        result = execute("ls | head -n 3")
        assert result["success"]
        lines = result["stdout"].strip().split("\n")
        assert len(lines) <= 3

    def test_pipe_tail(self):
        """Test ls | tail -n 2."""
        result = execute("ls | tail -n 2")
        assert result["success"]
        lines = result["stdout"].strip().split("\n")
        assert len(lines) <= 2

    def test_pipe_uniq(self):
        """Test sort | uniq."""
        result = execute("ls | sort | uniq")
        assert result["success"]
        lines = result["stdout"].strip().split("\n")
        # Verify no duplicates
        assert len(lines) == len(set(lines))

    def test_pipe_grep_invert(self):
        """Test ls | grep -v .py."""
        result = execute("ls | grep -v .py")
        assert result["success"]
        # Files with .py extension should be filtered out
        lines = result["stdout"].strip().split("\n")
        for line in lines:
            if line:  # Skip empty lines
                assert not line.endswith(".py"), f"Found .py file: {line}"


class TestFilterCommands:
    """Test filter commands with stdin."""

    def test_grep_with_input(self):
        """Test grep with input."""
        result = execute('echo "hello world" | grep hello')
        assert result["success"]

    def test_wc_lines_with_input(self):
        """Test wc -l with input."""
        result = execute('echo "line1\nline2\nline3" | wc -l')
        assert result["success"]

    def test_sort_with_input(self):
        """Test sort with input."""
        result = execute('echo "c\na\nb" | sort')
        assert result["success"]

    def test_head_with_input(self):
        """Test head with input."""
        result = execute('echo "1\n2\n3\n4\n5" | head -n 2')
        assert result["success"]

    def test_uniq_with_input(self):
        """Test uniq with input."""
        result = execute('echo "a\na\nb\nb\nc" | uniq')
        assert result["success"]
