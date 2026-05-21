# tests/test_path_trust.py
"""Tests for path trust management."""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch

from spark.security.path_trust import PathTrustManager
from spark.security import Decision


class TestPathTrustManager:
    """Tests for PathTrustManager."""

    def test_init(self):
        """Test initialization."""
        manager = PathTrustManager()
        assert manager.trusted_paths == set()

    def test_init_trust_current_dir(self):
        """Test initialization with trust_current_dir=True."""
        manager = PathTrustManager(trust_current_dir=True)
        assert len(manager.trusted_paths) == 1
        assert os.getcwd() in manager.trusted_paths

    def test_is_trusted_false(self, tmp_path):
        """Test checking untrusted path."""
        manager = PathTrustManager()
        assert manager.is_trusted(str(tmp_path)) is False

    def test_is_trusted_subpath(self, tmp_path):
        """Test checking subpath of trusted path."""
        manager = PathTrustManager()
        manager.add_trusted_path(str(tmp_path))
        subpath = tmp_path / "subdir" / "file.txt"
        assert manager.is_trusted(str(subpath)) is True

    def test_add_trusted_path(self, tmp_path):
        """Test adding trusted path."""
        manager = PathTrustManager()
        manager.add_trusted_path(str(tmp_path))
        assert manager.is_trusted(str(tmp_path)) is True

    def test_get_trusted_paths(self, tmp_path):
        """Test getting all trusted paths."""
        manager = PathTrustManager()
        manager.add_trusted_path(str(tmp_path))
        paths = manager.get_trusted_paths()
        assert len(paths) == 1

    def test_check_path_permission_plan_read(self):
        """Test plan mode allows read."""
        manager = PathTrustManager()
        decision = manager.check_path_permission("/tmp/test", "read", "plan")
        assert decision == Decision.ALLOW

    def test_check_path_permission_plan_write(self):
        """Test plan mode denies write."""
        manager = PathTrustManager()
        decision = manager.check_path_permission("/tmp/test", "write", "plan")
        assert decision == Decision.DENY

    def test_check_path_permission_ask_read(self):
        """Test ask mode allows read."""
        manager = PathTrustManager()
        decision = manager.check_path_permission("/tmp/test", "read", "ask")
        assert decision == Decision.ALLOW

    def test_check_path_permission_ask_write_untrusted(self):
        """Test ask mode confirms write for untrusted path."""
        manager = PathTrustManager()
        decision = manager.check_path_permission("/tmp/test", "write", "ask")
        assert decision == Decision.CONFIRM

    def test_check_path_permission_ask_write_trusted(self, tmp_path):
        """Test ask mode allows write for trusted path."""
        manager = PathTrustManager()
        manager.add_trusted_path(str(tmp_path))
        decision = manager.check_path_permission(str(tmp_path), "write", "ask")
        assert decision == Decision.ALLOW

    def test_check_path_permission_yolo_read(self):
        """Test yolo mode allows read."""
        manager = PathTrustManager()
        decision = manager.check_path_permission("/tmp/test", "read", "yolo")
        assert decision == Decision.ALLOW

    def test_check_path_permission_yolo_write_trusted(self, tmp_path):
        """Test yolo mode allows write for trusted path."""
        manager = PathTrustManager()
        manager.add_trusted_path(str(tmp_path))
        decision = manager.check_path_permission(str(tmp_path), "write", "yolo")
        assert decision == Decision.ALLOW

    def test_check_path_permission_yolo_write_untrusted(self):
        """Test yolo mode confirms write for untrusted path."""
        manager = PathTrustManager()
        decision = manager.check_path_permission("/tmp/test", "write", "yolo")
        assert decision == Decision.CONFIRM

    def test_is_trusted_exact_path(self, tmp_path):
        """Test exact path match."""
        manager = PathTrustManager()
        manager.add_trusted_path(str(tmp_path))
        assert manager.is_trusted(str(tmp_path)) is True

    def test_is_trusted_empty_path(self):
        """Test empty path returns False."""
        manager = PathTrustManager()
        assert manager.is_trusted("") is False
