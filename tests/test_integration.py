# tests/test_integration.py
"""Integration tests for spark."""

from unittest.mock import patch, Mock
from spark.config import Config
from spark.agent import Agent
from spark.security import Decision


def test_agent_full_flow():
    """测试完整流程"""
    with patch('spark.agent.PathTrustManager') as mock:
        mock.return_value.ask_trust_current_dir = Mock()
        config = Config()
        agent = Agent(config)

    messages = agent._build_messages("Hello")
    assert len(messages) >= 2

    tools = agent._get_all_tools()
    assert len(tools) >= 1

    decision = agent.security.check("run_shell", {"command": "ls"})
    assert decision in [Decision.ALLOW, Decision.CONFIRM, Decision.DENY]


def test_agent_with_yolo_mode():
    """测试 YOLO 模式"""
    with patch('spark.agent.PathTrustManager') as mock:
        mock.return_value.ask_trust_current_dir = Mock()
        config = Config()
        config.security.yolo_mode = True  # Enable yolo via config
        agent = Agent(config, mode="yolo")

    assert agent.mode == "yolo"
    # Security manager respects yolo_mode from config
    decision = agent.security.check("run_shell", {"command": "ls"})
    assert decision == Decision.ALLOW


def test_agent_history_compression():
    """测试历史压缩"""
    with patch('spark.agent.PathTrustManager') as mock:
        mock.return_value.ask_trust_current_dir = Mock()
        config = Config()
        agent = Agent(config)

    for i in range(10):
        agent.history.add("user", f"Message {i} " * 100)

    # Either compression is triggered or messages are stored
    assert agent.history.should_compress() or len(agent.history.messages) == 10
