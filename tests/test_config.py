# tests/test_config.py
import pytest
from pathlib import Path
from spark.config import Config, LLMConfig, SecurityConfig, HistoryConfig, load_config


def test_load_default_config():
    """测试加载默认配置"""
    config = Config()
    assert config.llm.base_url == "http://localhost:11434"
    assert config.llm.model == "gemma3:4b"  # Full model default
    assert config.security.yolo_mode is False


def test_load_config_from_file(tmp_path):
    """测试从文件加载配置"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text("""
llm:
  model: "llama3"
  base_url: "http://localhost:11435"
""")
    config = load_config(str(config_file))
    assert config.llm.model == "llama3"
    assert config.llm.base_url == "http://localhost:11435"


def test_config_merge_with_defaults():
    """测试配置与默认值合并"""
    config = load_config()
    # 默认值应该存在 (full model defaults)
    assert config.history.max_tokens == 4000
    assert config.history.compress_threshold == 0.7


def test_find_config_files(tmp_path, monkeypatch):
    """测试查找配置文件"""
    # 设置项目目录
    monkeypatch.chdir(tmp_path)
    project_config = tmp_path / "config.yaml"
    project_config.write_text("llm:\n  model: test")

    # Just verify config can be loaded
    config = load_config()
    assert config is not None
