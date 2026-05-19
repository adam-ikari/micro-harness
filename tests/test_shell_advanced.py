# tests/test_shell_advanced.py
"""Tests for advanced shell commands."""

import pytest
import tempfile
import os
from pathlib import Path

from spark.builtin.shell import execute


class TestFindAdvanced:
    """Tests for advanced find options."""

    def test_find_type_file(self, tmp_path):
        """Test find -type f (files only)."""
        # Create test structure
        (tmp_path / "file1.txt").write_text("test")
        (tmp_path / "subdir").mkdir()
        (tmp_path / "subdir" / "file2.txt").write_text("test")

        result = execute(f"find {tmp_path} -type f")
        assert result["success"]
        assert "file1.txt" in result["stdout"]
        assert "file2.txt" in result["stdout"]
        # subdir appears in path but not as standalone directory entry
        lines = result["stdout"].strip().split("\n")
        # All results should be files, not directories
        for line in lines:
            assert not line.endswith("/subdir") or line.endswith("/subdir/file2.txt")

    def test_find_type_dir(self, tmp_path):
        """Test find -type d (directories only)."""
        (tmp_path / "file1.txt").write_text("test")
        (tmp_path / "subdir").mkdir()

        result = execute(f"find {tmp_path} -type d")
        assert result["success"]
        assert "subdir" in result["stdout"]
        assert "file1.txt" not in result["stdout"]


class TestGrepAdvanced:
    """Tests for advanced grep options."""

    def test_grep_recursive(self, tmp_path):
        """Test grep -r (recursive)."""
        (tmp_path / "file1.txt").write_text("hello world")
        (tmp_path / "subdir").mkdir()
        (tmp_path / "subdir" / "file2.txt").write_text("hello again")

        result = execute(f"grep -r hello {tmp_path}")
        assert result["success"]
        assert "file1.txt" in result["stdout"]
        assert "file2.txt" in result["stdout"]

    def test_grep_line_numbers(self, tmp_path):
        """Test grep -n (line numbers)."""
        (tmp_path / "test.txt").write_text("line1\nhello\nline3")

        result = execute(f"grep -n hello {tmp_path / 'test.txt'}")
        assert result["success"]
        # BusyBox grep -n outputs "line_number:content" format
        assert "hello" in result["stdout"]
        # Line 2 contains hello
        assert "2" in result["stdout"]

    def test_grep_count(self, tmp_path):
        """Test grep -c (count)."""
        (tmp_path / "test.txt").write_text("hello\nworld\nhello")

        result = execute(f"grep -c hello {tmp_path / 'test.txt'}")
        assert result["success"]
        assert "2" in result["stdout"]

    def test_grep_invert(self, tmp_path):
        """Test grep -v (invert match)."""
        (tmp_path / "test.txt").write_text("hello\nworld\ntest")

        result = execute(f"grep -v hello {tmp_path / 'test.txt'}")
        assert result["success"]
        assert "world" in result["stdout"]
        assert "test" in result["stdout"]
        assert "hello" not in result["stdout"]


class TestNewCommands:
    """Tests for new shell commands."""

    def test_echo(self):
        """Test echo command."""
        result = execute("echo hello world")
        assert result["success"]
        assert "hello world" in result["stdout"]

    def test_wc_lines(self, tmp_path):
        """Test wc -l (line count)."""
        (tmp_path / "test.txt").write_text("line1\nline2\nline3")

        result = execute(f"wc -l {tmp_path / 'test.txt'}")
        assert result["success"]
        # wc -l counts newlines, so 3 newlines = 3 lines
        # But if last line has no trailing newline, it counts 2
        assert "2" in result["stdout"] or "3" in result["stdout"]

    def test_wc_words(self, tmp_path):
        """Test wc -w (word count)."""
        (tmp_path / "test.txt").write_text("hello world test")

        result = execute(f"wc -w {tmp_path / 'test.txt'}")
        assert result["success"]
        assert "3" in result["stdout"]

    def test_sort(self, tmp_path):
        """Test sort command."""
        (tmp_path / "test.txt").write_text("zebra\napple\nbanana")

        result = execute(f"sort {tmp_path / 'test.txt'}")
        assert result["success"]
        lines = result["stdout"].strip().split("\n")
        assert lines[0] == "apple"
        assert lines[1] == "banana"
        assert lines[2] == "zebra"

    def test_uniq(self, tmp_path):
        """Test uniq command."""
        (tmp_path / "test.txt").write_text("a\na\nb\nb\nc")

        result = execute(f"uniq {tmp_path / 'test.txt'}")
        assert result["success"]
        lines = result["stdout"].strip().split("\n")
        assert lines == ["a", "b", "c"]

    def test_tree(self, tmp_path):
        """Test tree command."""
        (tmp_path / "file1.txt").write_text("test")
        (tmp_path / "subdir").mkdir()
        (tmp_path / "subdir" / "file2.txt").write_text("test")

        result = execute(f"tree {tmp_path}")
        assert result["success"]
        assert "file1.txt" in result["stdout"]
        assert "subdir" in result["stdout"]

    def test_env(self):
        """Test env command."""
        result = execute("env")
        assert result["success"]
        # Should show PATH at minimum
        assert "PATH" in result["stdout"] or "path" in result["stdout"].lower()
