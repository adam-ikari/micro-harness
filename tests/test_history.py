# tests/test_history.py
import pytest
from zero_agent.history import HistoryManager
from zero_agent.config import HistoryConfig


def test_history_add():
    """测试添加消息"""
    config = HistoryConfig()
    history = HistoryManager(config)

    history.add("user", "Hello")
    history.add("assistant", "Hi there")

    assert len(history.messages) == 2
    assert history.messages[0]["role"] == "user"


def test_history_get_messages():
    """测试获取消息列表"""
    config = HistoryConfig()
    history = HistoryManager(config)

    history.add("user", "Hello")
    history.add("assistant", "Hi")

    messages = history.get_messages()
    assert len(messages) == 2


def test_history_clear():
    """测试清空历史"""
    config = HistoryConfig()
    history = HistoryManager(config)

    history.add("user", "Hello")
    history.clear()

    assert len(history.messages) == 0


def test_history_should_compress():
    """测试压缩判断"""
    config = HistoryConfig(max_tokens=100, compress_threshold=0.8)
    history = HistoryManager(config)

    # 添加足够多的消息触发压缩阈值
    for i in range(10):
        history.add("user", f"Message {i} " * 50)  # 每条约 300 字符

    # 应该需要压缩
    assert history.should_compress()


def test_history_compress():
    """测试历史压缩"""
    config = HistoryConfig(max_tokens=1000)
    history = HistoryManager(config)

    # 添加多条消息
    for i in range(5):
        history.add("user", f"User message {i}")
        history.add("assistant", f"Assistant response {i}")

    original_count = len(history.messages)

    # 模拟压缩（用 mock LLM）
    from unittest.mock import Mock
    mock_llm = Mock()
    mock_llm.generate_summary.return_value = "Summary of previous conversation"

    history.compress(mock_llm)

    # 压缩后消息应该减少
    assert len(history.messages) < original_count
    assert history.messages[0]["role"] == "system"  # 摘要作为 system 消息
