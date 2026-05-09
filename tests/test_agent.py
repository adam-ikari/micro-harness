# tests/test_agent.py
import pytest
from unittest.mock import Mock, patch
from micro_harness.agent import Agent
from micro_harness.config import Config, LLMConfig, SecurityConfig, HistoryConfig


def test_agent_init():
    """测试 Agent 初始化"""
    config = Config()
    agent = Agent(config)

    assert agent.config == config
    assert agent.history is not None
    assert agent.security is not None


def test_agent_build_messages():
    """测试构建消息"""
    config = Config()
    agent = Agent(config)

    messages = agent._build_messages("Hello")

    # 应包含用户消息
    assert len(messages) >= 1
    assert messages[-1]["role"] == "user"
    assert messages[-1]["content"] == "Hello"


def test_agent_build_messages_with_history():
    """测试构建消息包含历史"""
    config = Config()
    agent = Agent(config)

    # 添加历史
    agent.history.add("user", "Previous message")
    agent.history.add("assistant", "Previous response")

    messages = agent._build_messages("New message")

    # 应包含历史消息
    assert len(messages) >= 3


def test_agent_build_messages_with_skills():
    """测试构建消息包含 skills"""
    config = Config()
    agent = Agent(config)

    # 模拟 skills
    agent.skills.skills = {"test": {"content": "Test skill content"}}

    messages = agent._build_messages("Hello")

    # 应包含 skills prompt
    assert any("Test skill content" in m.get("content", "") for m in messages)


def test_agent_get_all_tools():
    """测试获取所有工具"""
    config = Config()
    agent = Agent(config)

    tools = agent._get_all_tools()

    # 应包含内置工具
    assert len(tools) >= 1
    assert any(t["name"] == "run_shell" for t in tools)
