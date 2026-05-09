# src/zero_agent/fs/operations.py
"""Cross-platform file system operations.

All operations use Python's pathlib, shutil, and os modules
to ensure Windows compatibility without relying on shell commands.
"""

import os
import shutil
import logging
from pathlib import Path
from typing import Optional, Union, List
from datetime import datetime

logger = logging.getLogger(__name__)

PathLike = Union[str, Path]


class FileSystemOperations:
    """Cross-platform file system operations."""

    @staticmethod
    def list_dir(path: PathLike = ".",
                 all_files: bool = False,
                 long_format: bool = False) -> List[str]:
        """List directory contents (cross-platform ls/dir).

        Args:
            path: Directory path
            all_files: Show hidden files
            long_format: Show detailed info

        Returns:
            List of file names or detailed strings
        """
        path = Path(path)
        if not path.exists():
            return [f"Error: {path} does not exist"]

        if not path.is_dir():
            return [f"Error: {path} is not a directory"]

        items = []
        try:
            for item in sorted(path.iterdir()):
                # Skip hidden files unless all_files
                if not all_files and item.name.startswith('.'):
                    continue

                if long_format:
                    stat = item.stat()
                    size = stat.st_size
                    mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
                    item_type = 'd' if item.is_dir() else '-'
                    items.append(f"{item_type} {size:>10} {mtime} {item.name}")
                else:
                    items.append(item.name)
        except PermissionError as e:
            return [f"Error: Permission denied - {e}"]

        return items

    @staticmethod
    def read_file(path: PathLike,
                  lines: Optional[int] = None,
                  tail: bool = False) -> str:
        """Read file contents (cross-platform cat/type).

        Args:
            path: File path
            lines: Number of lines to read (None = all)
            tail: Read from end (like tail)

        Returns:
            File contents as string
        """
        path = Path(path)
        if not path.exists():
            return f"Error: {path} does not exist"

        if not path.is_file():
            return f"Error: {path} is not a file"

        try:
            if lines is None:
                return path.read_text(encoding='utf-8', errors='replace')

            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                all_lines = f.readlines()

            if tail:
                return ''.join(all_lines[-lines:])
            return ''.join(all_lines[:lines])
        except PermissionError as e:
            return f"Error: Permission denied - {e}"
        except Exception as e:
            return f"Error: {e}"

    @staticmethod
    def write_file(path: PathLike, content: str, append: bool = False) -> str:
        """Write content to file (cross-platform echo/cat >).

        Args:
            path: File path
            content: Content to write
            append: Append to file instead of overwrite

        Returns:
            Success message or error
        """
        path = Path(path)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            mode = 'a' if append else 'w'
            with open(path, mode, encoding='utf-8') as f:
                f.write(content)
            return f"Wrote {len(content)} chars to {path}"
        except PermissionError as e:
            return f"Error: Permission denied - {e}"
        except Exception as e:
            return f"Error: {e}"

    @staticmethod
    def copy(src: PathLike, dst: PathLike, recursive: bool = False) -> str:
        """Copy file or directory (cross-platform cp).

        Args:
            src: Source path
            dst: Destination path
            recursive: Copy directories recursively

        Returns:
            Success message or error
        """
        src, dst = Path(src), Path(dst)

        if not src.exists():
            return f"Error: {src} does not exist"

        try:
            if src.is_file():
                shutil.copy2(src, dst)
                return f"Copied {src} to {dst}"
            elif src.is_dir():
                if not recursive:
                    return f"Error: {src} is a directory, use -r for recursive"
                shutil.copytree(src, dst)
                return f"Copied directory {src} to {dst}"
        except PermissionError as e:
            return f"Error: Permission denied - {e}"
        except Exception as e:
            return f"Error: {e}"

    @staticmethod
    def move(src: PathLike, dst: PathLike) -> str:
        """Move file or directory (cross-platform mv).

        Args:
            src: Source path
            dst: Destination path

        Returns:
            Success message or error
        """
        src, dst = Path(src), Path(dst)

        if not src.exists():
            return f"Error: {src} does not exist"

        try:
            shutil.move(str(src), str(dst))
            return f"Moved {src} to {dst}"
        except PermissionError as e:
            return f"Error: Permission denied - {e}"
        except Exception as e:
            return f"Error: {e}"

    @staticmethod
    def remove(path: PathLike, recursive: bool = False) -> str:
        """Remove file or directory (cross-platform rm).

        Args:
            path: Path to remove
            recursive: Remove directories recursively

        Returns:
            Success message or error
        """
        path = Path(path)

        if not path.exists():
            return f"Error: {path} does not exist"

        try:
            if path.is_file():
                path.unlink()
                return f"Removed {path}"
            elif path.is_dir():
                if not recursive:
                    return f"Error: {path} is a directory, use -r for recursive"
                shutil.rmtree(path)
                return f"Removed directory {path}"
        except PermissionError as e:
            return f"Error: Permission denied - {e}"
        except Exception as e:
            return f"Error: {e}"

    @staticmethod
    def make_dir(path: PathLike, parents: bool = False) -> str:
        """Create directory (cross-platform mkdir).

        Args:
            path: Directory path
            parents: Create parent directories

        Returns:
            Success message or error
        """
        path = Path(path)

        if path.exists():
            return f"Error: {path} already exists"

        try:
            path.mkdir(parents=parents, exist_ok=False)
            return f"Created directory {path}"
        except PermissionError as e:
            return f"Error: Permission denied - {e}"
        except Exception as e:
            return f"Error: {e}"

    @staticmethod
    def touch(path: PathLike) -> str:
        """Create empty file or update timestamp (cross-platform touch).

        Args:
            path: File path

        Returns:
            Success message or error
        """
        path = Path(path)

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.exists():
                path.touch()
                return f"Updated timestamp for {path}"
            else:
                path.write_text('')
                return f"Created {path}"
        except PermissionError as e:
            return f"Error: Permission denied - {e}"
        except Exception as e:
            return f"Error: {e}"

    @staticmethod
    def find(path: PathLike = ".",
             name: Optional[str] = None,
             file_type: Optional[str] = None) -> List[str]:
        """Find files (cross-platform find).

        Args:
            path: Starting directory
            name: Name pattern (glob)
            file_type: 'f' for files, 'd' for directories

        Returns:
            List of matching paths
        """
        path = Path(path)

        if not path.exists():
            return [f"Error: {path} does not exist"]

        results = []
        try:
            for item in path.rglob(name or '*'):
                if file_type == 'f' and not item.is_file():
                    continue
                if file_type == 'd' and not item.is_dir():
                    continue
                results.append(str(item))
        except PermissionError:
            pass  # Skip directories we can't access

        return results

    @staticmethod
    def grep(pattern: str, path: PathLike,
             ignore_case: bool = False) -> List[str]:
        """Search in files (cross-platform grep).

        Args:
            pattern: Search pattern
            path: File or directory path
            ignore_case: Case insensitive search

        Returns:
            List of matching lines
        """
        import re

        path = Path(path)
        flags = re.IGNORECASE if ignore_case else 0
        regex = re.compile(pattern, flags)

        results = []
        try:
            if path.is_file():
                with open(path, 'r', encoding='utf-8', errors='replace') as f:
                    for i, line in enumerate(f, 1):
                        if regex.search(line):
                            results.append(f"{path}:{i}:{line.rstrip()}")
            elif path.is_dir():
                for file in path.rglob('*'):
                    if file.is_file():
                        try:
                            with open(file, 'r', encoding='utf-8', errors='replace') as f:
                                for i, line in enumerate(f, 1):
                                    if regex.search(line):
                                        results.append(f"{file}:{i}:{line.rstrip()}")
                        except (PermissionError, UnicodeDecodeError):
                            pass
        except PermissionError as e:
            return [f"Error: Permission denied - {e}"]

        return results

    @staticmethod
    def pwd() -> str:
        """Get current working directory (cross-platform pwd)."""
        return str(Path.cwd())

    @staticmethod
    def which(command: str) -> Optional[str]:
        """Find command in PATH (cross-platform which/where).

        Args:
            command: Command name

        Returns:
            Full path to command or None
        """
        return shutil.which(command)

    @staticmethod
    def get_file_info(path: PathLike) -> dict:
        """Get file information (cross-platform stat).

        Args:
            path: File path

        Returns:
            Dictionary with file info
        """
        path = Path(path)

        if not path.exists():
            return {"error": f"{path} does not exist"}

        stat = path.stat()
        return {
            "path": str(path),
            "type": "directory" if path.is_dir() else "file",
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "permissions": oct(stat.st_mode)[-3:],
        }
