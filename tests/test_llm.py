# tests/test_llm.py
import pytest
from unittest.mock import Mock, patch
from zero_agent.llm import OllamaAdapter
from zero_agent.config import LLMConfig


def test_ollama_adapter_init():
    """测试适配器初始化"""
    config = LLMConfig(base_url="http://localhost:11434", model="gemma3:4b")
    adapter = OllamaAdapter(config)
    assert adapter.base_url == "http://localhost:11434"
    assert adapter.model == "gemma3:4b"


def test_ollama_adapter_build_tools():
    """测试工具定义构建（小模型优化：精简描述）"""
    config = LLMConfig()
    adapter = OllamaAdapter(config)

    tools = [
        {"name": "run_shell", "description": "Execute shell command", "parameters": {}}
    ]

    simplified = adapter._simplify_tools(tools)
    assert len(simplified) == 1
    assert simplified[0]["type"] == "function"
    assert "name" in simplified[0]["function"]


def test_ollama_adapter_estimate_tokens():
    """测试 token 估算"""
    config = LLMConfig()
    adapter = OllamaAdapter(config)

    messages = [
        {"role": "user", "content": "Hello world"},
        {"role": "assistant", "content": "Hi there"},
    ]

    tokens = adapter.estimate_tokens(messages)
    # 粗略估算：每个消息约 20 tokens
    assert tokens > 0
    assert tokens < 1000
