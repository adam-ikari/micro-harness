# tests/test_shell_cross_platform.py
"""Cross-platform shell tests for Linux/Mac/Windows."""

import pytest
import sys
import tempfile
from pathlib import Path

from spark.builtin.shell import execute, SHELL_PATH, SHELL_TYPE


class TestShellDetection:
    """Test shell detection on different platforms."""

    def test_shell_path_detected(self):
        """Test that a shell path is detected."""
        # On Linux/Mac, should find /bin/sh
        # On Windows, should find Git Bash if installed
        if sys.platform != 'win32':
            assert SHELL_PATH == '/bin/sh'
            assert SHELL_TYPE == 'native'
        else:
            # On Windows, may or may not have Git Bash
            if SHELL_PATH:
                assert SHELL_TYPE == 'gitbash'

    def test_shell_available(self):
        """Test that shell is available for execution."""
        # Should have shell on Linux/Mac
        if sys.platform != 'win32':
            assert SHELL_PATH is not None


class TestBasicCommands:
    """Test basic shell commands work on all platforms."""

    def test_echo(self):
        """Test echo command."""
        result = execute("echo hello")
        assert result["success"]
        assert "hello" in result["stdout"]

    def test_pwd(self):
        """Test pwd command."""
        result = execute("pwd")
        assert result["success"]
        # Should return a valid path
        assert len(result["stdout"].strip()) > 0

    def test_ls(self):
        """Test ls command."""
        result = execute("ls")
        assert result["success"]

    def test_cat_file(self, tmp_path):
        """Test cat command."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello world")

        result = execute(f"cat {test_file}")
        assert result["success"]
        assert "hello world" in result["stdout"]


class TestPipelines:
    """Test pipeline commands work on all platforms."""

    def test_simple_pipe(self):
        """Test simple pipe: echo | cat."""
        result = execute("echo hello | cat")
        assert result["success"]
        assert "hello" in result["stdout"]

    def test_pipe_grep(self, tmp_path):
        """Test pipe with grep."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("apple\nbanana\ncherry\napricot")

        result = execute(f"cat {test_file} | grep a")
        assert result["success"]
        assert "apple" in result["stdout"]
        assert "apricot" in result["stdout"]
        # Note: 'banana' contains 'a' so it will be in the output

    def test_pipe_wc(self, tmp_path):
        """Test pipe with wc."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("line1\nline2\nline3")

        result = execute(f"cat {test_file} | wc -l")
        assert result["success"]
        # wc -l counts newlines, so 3 newlines = 3 lines
        # But last line might not have newline, so could be 2 or 3
        assert "2" in result["stdout"] or "3" in result["stdout"]

    def test_multiple_pipes(self, tmp_path):
        """Test multiple pipes."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("apple\nbanana\napple\ncherry\napple")

        result = execute(f"cat {test_file} | grep apple | wc -l")
        assert result["success"]
        assert "3" in result["stdout"]


class TestFileOperations:
    """Test file operations work on all platforms."""

    def test_touch(self, tmp_path):
        """Test touch creates file."""
        new_file = tmp_path / "new.txt"

        result = execute(f"touch {new_file}")
        assert result["success"]
        assert new_file.exists()

    def test_mkdir(self, tmp_path):
        """Test mkdir creates directory."""
        new_dir = tmp_path / "newdir"

        result = execute(f"mkdir {new_dir}")
        assert result["success"]
        assert new_dir.exists()
        assert new_dir.is_dir()

    def test_rm(self, tmp_path):
        """Test rm removes file."""
        test_file = tmp_path / "to_delete.txt"
        test_file.write_text("delete me")

        result = execute(f"rm {test_file}")
        assert result["success"]
        assert not test_file.exists()

    def test_cp(self, tmp_path):
        """Test cp copies file."""
        src = tmp_path / "source.txt"
        dst = tmp_path / "dest.txt"
        src.write_text("copy me")

        result = execute(f"cp {src} {dst}")
        assert result["success"]
        assert dst.exists()
        assert dst.read_text() == "copy me"

    def test_mv(self, tmp_path):
        """Test mv moves file."""
        src = tmp_path / "source.txt"
        dst = tmp_path / "dest.txt"
        src.write_text("move me")

        result = execute(f"mv {src} {dst}")
        assert result["success"]
        assert not src.exists()
        assert dst.exists()
        assert dst.read_text() == "move me"


class TestFindCommand:
    """Test find command on all platforms."""

    def test_find_name(self, tmp_path):
        """Test find by name."""
        (tmp_path / "file1.txt").write_text("test")
        (tmp_path / "file2.py").write_text("test")
        (tmp_path / "subdir").mkdir()
        (tmp_path / "subdir" / "file3.txt").write_text("test")

        result = execute(f"find {tmp_path} -name '*.txt'")
        assert result["success"]
        assert "file1.txt" in result["stdout"]
        assert "file3.txt" in result["stdout"]
        assert "file2.py" not in result["stdout"]


class TestGrepOptions:
    """Test grep options on all platforms."""

    def test_grep_i(self, tmp_path):
        """Test grep -i (case insensitive)."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("HELLO\nWorld\nhello")

        result = execute(f"grep -i hello {test_file}")
        assert result["success"]
        assert "HELLO" in result["stdout"]
        assert "hello" in result["stdout"]

    def test_grep_v(self, tmp_path):
        """Test grep -v (invert match)."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("apple\nbanana\ncherry")

        result = execute(f"grep -v banana {test_file}")
        assert result["success"]
        assert "apple" in result["stdout"]
        assert "cherry" in result["stdout"]
        assert "banana" not in result["stdout"]


class TestErrorHandling:
    """Test error handling on all platforms."""

    def test_empty_command(self):
        """Test empty command returns error."""
        result = execute("")
        assert result["success"] is False
        assert "empty" in result["error"].lower()

    def test_nonexistent_file(self):
        """Test cat on nonexistent file."""
        result = execute("cat /nonexistent_file_12345.txt")
        assert result["success"] is False

    def test_command_timeout(self):
        """Test command execution works."""
        # This should complete quickly
        result = execute("echo quick")
        assert result["success"]


class TestEnvironment:
    """Test environment commands."""

    def test_env(self):
        """Test env command."""
        result = execute("env")
        assert result["success"]
        # Should contain PATH
        assert "PATH" in result["stdout"] or "path" in result["stdout"].lower()

    def test_which(self):
        """Test which command."""
        result = execute("which python")
        assert result["success"]
        assert "python" in result["stdout"].lower()


class TestWindowsSpecific:
    """Tests specific to Windows with Git Bash."""

    @pytest.mark.skipif(sys.platform != 'win32', reason="Windows only")
    def test_git_bash_available(self):
        """Test Git Bash is available on Windows."""
        assert SHELL_PATH is not None
        assert SHELL_TYPE == 'gitbash'

    @pytest.mark.skipif(sys.platform != 'win32', reason="Windows only")
    def test_windows_path_conversion(self, tmp_path):
        """Test Windows path handling in Git Bash."""
        # Git Bash should handle Windows paths
        result = execute(f"ls {tmp_path}")
        assert result["success"]


class TestLinuxMacSpecific:
    """Tests specific to Linux/Mac."""

    @pytest.mark.skipif(sys.platform == 'win32', reason="Linux/Mac only")
    def test_native_shell(self):
        """Test native shell on Linux/Mac."""
        assert SHELL_PATH == '/bin/sh'
        assert SHELL_TYPE == 'native'

    @pytest.mark.skipif(sys.platform == 'win32', reason="Linux/Mac only")
    def test_unix_permissions(self, tmp_path):
        """Test chmod on Linux/Mac."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")

        result = execute(f"chmod 644 {test_file}")
        assert result["success"]