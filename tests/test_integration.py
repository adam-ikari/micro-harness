# tests/test_integration.py
"""Integration tests for zero-agent."""

from zero_agent.config import load_config
from zero_agent.agent import Agent
from zero_agent.security import Decision


def test_agent_full_flow():
    """测试完整流程"""
    config = load_config()
    agent = Agent(config)

    messages = agent._build_messages("Hello")
    assert len(messages) >= 2

    tools = agent._get_all_tools()
    assert len(tools) >= 1

    decision = agent.security.check("run_shell", {"command": "ls"})
    assert decision in [Decision.ALLOW, Decision.CONFIRM, Decision.DENY]


def test_agent_with_yolo_mode():
    """测试 YOLO 模式"""
    config = load_config()
    agent = Agent(config, yolo=True)

    assert agent.security.yolo is True
    decision = agent.security.check("run_shell", {"command": "ls"})
    assert decision == Decision.ALLOW


def test_agent_history_compression():
    """测试历史压缩"""
    config = load_config()
    agent = Agent(config)

    for i in range(10):
        agent.history.add("user", f"Message {i} " * 100)

    assert agent.history.should_compress() or len(agent.history.messages) < 10
