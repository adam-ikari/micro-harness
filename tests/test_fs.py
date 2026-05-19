# tests/test_fs.py
"""Tests for filesystem operations."""

import pytest
import tempfile
from pathlib import Path
from spark.fs.operations import FileSystemOperations


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests."""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


def test_fs_operations_init():
    """Test FS operations initialization."""
    fs = FileSystemOperations()
    assert fs is not None


def test_fs_list_dir(temp_dir):
    """Test listing directory."""
    # Create some files
    (temp_dir / "file1.txt").write_text("content1")
    (temp_dir / "file2.txt").write_text("content2")

    items = FileSystemOperations.list_dir(str(temp_dir))
    assert len(items) == 2
    assert any("file1.txt" in str(item) for item in items)


def test_fs_list_dir_not_exists():
    """Test listing nonexistent directory."""
    items = FileSystemOperations.list_dir("/nonexistent/path")
    assert len(items) == 1
    assert "Error" in items[0]


def test_fs_list_dir_all_files(temp_dir):
    """Test listing with hidden files."""
    (temp_dir / "visible.txt").write_text("content")
    (temp_dir / ".hidden").write_text("hidden content")

    items_all = FileSystemOperations.list_dir(str(temp_dir), all_files=True)
    assert len(items_all) >= 1


def test_fs_list_dir_long_format(temp_dir):
    """Test listing with long format."""
    (temp_dir / "test.txt").write_text("content")

    items = FileSystemOperations.list_dir(str(temp_dir), long_format=True)
    assert len(items) >= 1


def test_fs_read_file(temp_dir):
    """Test reading a file."""
    test_file = temp_dir / "test.txt"
    test_file.write_text("Hello World")

    content = FileSystemOperations.read_file(str(test_file))
    assert content == "Hello World"


def test_fs_read_file_not_exists(temp_dir):
    """Test reading nonexistent file returns error message."""
    result = FileSystemOperations.read_file(str(temp_dir / "nonexistent.txt"))
    assert "Error" in result or result == ""


def test_fs_write_file(temp_dir):
    """Test writing a file."""
    test_file = temp_dir / "output.txt"
    FileSystemOperations.write_file(str(test_file), "Test content")

    assert test_file.exists()
    assert test_file.read_text() == "Test content"


def test_fs_write_file_append(temp_dir):
    """Test appending to file."""
    test_file = temp_dir / "append.txt"
    test_file.write_text("Initial")

    FileSystemOperations.write_file(str(test_file), " Added", append=True)

    assert test_file.read_text() == "Initial Added"


def test_fs_make_dir(temp_dir):
    """Test creating directory."""
    new_dir = temp_dir / "new_folder"
    result = FileSystemOperations.make_dir(str(new_dir))

    assert new_dir.exists()
    assert new_dir.is_dir()


def test_fs_make_dir_parents(temp_dir):
    """Test creating nested directories."""
    new_dir = temp_dir / "parent" / "child" / "grandchild"
    result = FileSystemOperations.make_dir(str(new_dir), parents=True)

    assert new_dir.exists()


def test_fs_remove_file(temp_dir):
    """Test removing file."""
    test_file = temp_dir / "to_delete.txt"
    test_file.write_text("delete me")

    FileSystemOperations.remove(str(test_file))
    assert not test_file.exists()


def test_fs_copy(temp_dir):
    """Test copying file."""
    src = temp_dir / "source.txt"
    src.write_text("original content")

    dst = temp_dir / "copy.txt"
    FileSystemOperations.copy(str(src), str(dst))

    assert dst.exists()
    assert dst.read_text() == "original content"


def test_fs_move(temp_dir):
    """Test moving file."""
    src = temp_dir / "source.txt"
    src.write_text("content to move")

    dst = temp_dir / "moved.txt"
    FileSystemOperations.move(str(src), str(dst))

    assert not src.exists()
    assert dst.exists()
    assert dst.read_text() == "content to move"


def test_fs_pwd():
    """Test pwd returns current directory."""
    result = FileSystemOperations.pwd()
    assert result is not None
    assert len(result) > 0


def test_fs_touch(temp_dir):
    """Test touch creates file."""
    test_file = temp_dir / "touched.txt"
    FileSystemOperations.touch(str(test_file))

    assert test_file.exists()


def test_fs_get_file_info(temp_dir):
    """Test getting file info."""
    test_file = temp_dir / "info.txt"
    test_file.write_text("test content")

    info = FileSystemOperations.get_file_info(str(test_file))
    assert "size" in info or "path" in info


def test_fs_find(temp_dir):
    """Test find files."""
    (temp_dir / "file1.py").write_text("python")
    (temp_dir / "file2.txt").write_text("text")

    results = FileSystemOperations.find(str(temp_dir), name="*.py")
    assert len(results) >= 1


def test_fs_grep(temp_dir):
    """Test grep in files."""
    test_file = temp_dir / "test.py"
    test_file.write_text("def hello():\n    print('hello')\n")

    results = FileSystemOperations.grep("hello", str(temp_dir))
    assert len(results) >= 1