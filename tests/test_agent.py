# tests/test_agent.py
import pytest
from unittest.mock import Mock, patch, MagicMock
from spark.agent import Agent
from spark.config import Config, LLMConfig, SecurityConfig, HistoryConfig
from spark.security import Decision
from spark.llm import ChatResponse


@pytest.fixture
def mock_path_trust():
    """Mock path trust to avoid stdin prompts."""
    with patch('spark.agent.PathTrustManager') as mock:
        mock.return_value.ask_trust_current_dir = Mock()
        yield mock


@pytest.fixture
def mock_llm():
    """Mock LLM adapter."""
    with patch('spark.agent.OllamaAdapter') as mock:
        mock_instance = MagicMock()
        mock_instance.chat.return_value = ChatResponse(content="Test response", tool_calls=None)
        mock.return_value = mock_instance
        yield mock_instance


def test_agent_init(mock_path_trust):
    """测试 Agent 初始化"""
    config = Config()
    agent = Agent(config)

    assert agent.config == config
    assert agent.history is not None
    assert agent.security is not None


def test_agent_build_messages(mock_path_trust):
    """测试构建消息"""
    config = Config()
    agent = Agent(config)

    messages = agent._build_messages("Hello")

    # 应包含用户消息
    assert len(messages) >= 1
    assert messages[-1]["role"] == "user"
    assert messages[-1]["content"] == "Hello"


def test_agent_build_messages_with_history(mock_path_trust):
    """测试构建消息包含历史"""
    config = Config()
    agent = Agent(config)

    # 添加历史
    agent.history.add("user", "Previous message")
    agent.history.add("assistant", "Previous response")

    messages = agent._build_messages("New message")

    # 应包含历史消息
    assert len(messages) >= 3


def test_agent_build_messages_with_skills(mock_path_trust):
    """测试构建消息包含 skills"""
    config = Config()
    agent = Agent(config)

    # 模拟 skills
    agent.skills.skills = {"test": {"content": "Test skill content"}}

    messages = agent._build_messages("Hello")

    # 应包含 skills prompt
    assert any("Test skill content" in m.get("content", "") for m in messages)


def test_agent_get_all_tools(mock_path_trust):
    """测试获取所有工具"""
    config = Config()
    agent = Agent(config)

    tools = agent._get_all_tools()

    # 应包含内置工具
    assert len(tools) >= 1
    # Tool name is "Bash" not "run_shell"
    assert any(t["name"] == "Bash" for t in tools)


def test_agent_mode_initialization(mock_path_trust):
    """Test agent mode initialization."""
    config = Config()

    agent_plan = Agent(config, mode="plan")
    assert agent_plan.mode == "plan"

    agent_yolo = Agent(config, mode="yolo")
    assert agent_yolo.mode == "yolo"


def test_agent_lang_initialization(mock_path_trust):
    """Test agent language initialization."""
    config = Config()

    agent_zh = Agent(config, lang="zh")
    assert agent_zh.lang == "zh"

    agent_ja = Agent(config, lang="ja")
    assert agent_ja.lang == "ja"


def test_agent_translation(mock_path_trust):
    """Test translation method."""
    config = Config()
    agent = Agent(config, lang="en")

    welcome = agent.t("welcome")
    assert welcome is not None
    assert len(welcome) > 0


def test_agent_translation_chinese(mock_path_trust):
    """Test Chinese translation."""
    config = Config()
    agent = Agent(config, lang="zh")

    welcome = agent.t("welcome")
    assert "Spark" in welcome or "模式" in welcome


def test_agent_get_tool_decision_yolo(mock_path_trust):
    """Test tool decision in yolo mode."""
    config = Config()
    config.security.yolo_mode = True
    agent = Agent(config, mode="yolo")

    decision = agent._get_tool_decision("Bash", {"command": "ls"})
    assert decision == Decision.ALLOW


def test_agent_get_tool_decision_plan(mock_path_trust):
    """Test tool decision in plan mode."""
    config = Config()
    agent = Agent(config, mode="plan")

    # Write command should be denied in plan mode
    decision = agent._get_tool_decision("Bash", {"command": "echo test > file.txt"})
    assert decision == Decision.DENY


def test_agent_is_write_command(mock_path_trust):
    """Test write command detection."""
    config = Config()
    agent = Agent(config)

    assert agent._is_write_command("echo test > file.txt") is True
    assert agent._is_write_command("ls -la") is False
    assert agent._is_write_command("rm file.txt") is True


def test_agent_cycle_mode(mock_path_trust):
    """Test mode cycling."""
    config = Config()
    agent = Agent(config, mode="ask")

    agent._cycle_mode()
    assert agent.mode == "yolo"

    agent._cycle_mode()
    assert agent.mode == "plan"

    agent._cycle_mode()
    assert agent.mode == "ask"


def test_agent_cycle_lang(mock_path_trust):
    """Test language cycling."""
    config = Config()
    agent = Agent(config, lang="en")

    agent._cycle_lang()
    assert agent.lang == "zh"

    agent._cycle_lang()
    assert agent.lang == "ja"

    agent._cycle_lang()
    assert agent.lang == "en"


def test_agent_run_once(mock_path_trust, mock_llm):
    """Test run_once method."""
    config = Config()
    agent = Agent(config)

    result = agent.run_once("Hello")
    assert result is not None


def test_agent_relevant_skills_prompt(mock_path_trust):
    """Test getting relevant skills prompt."""
    config = Config()
    agent = Agent(config)

    # No skills loaded
    prompt = agent._get_relevant_skills_prompt("test query")
    # Should return empty string when no skills match
    assert prompt is not None


def test_agent_process_response(mock_path_trust, mock_llm):
    """Test response processing."""
    config = Config()
    agent = Agent(config)

    response = ChatResponse(content="Hello, how can I help?", tool_calls=None)
    result = agent._process_response(response)

    assert "Hello" in result


def test_agent_process_response_with_tool_calls(mock_path_trust, mock_llm):
    """Test response processing with tool calls."""
    config = Config()
    config.security.yolo_mode = True
    agent = Agent(config, mode="yolo")

    # Mock shell execute
    with patch('spark.agent.shell_execute') as mock_shell:
        mock_shell.return_value = {"success": True, "output": "file1.txt\nfile2.txt", "returncode": 0}

        response = ChatResponse(
            content="Let me check",
            tool_calls=[{"function": {"name": "Bash", "arguments": {"command": "ls"}}}]
        )

        result = agent._process_response(response)
        assert result is not None
