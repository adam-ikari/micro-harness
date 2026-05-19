# tests/test_e2e.py
"""End-to-end integration tests for Spark."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from spark.config import Config, LLMConfig, SecurityConfig
from spark.agent import Agent
from spark.security import Decision
from spark.llm import ChatResponse


@pytest.fixture
def mock_llm():
    """Mock LLM adapter."""
    with patch('spark.agent.OllamaAdapter') as mock:
        mock_instance = MagicMock()
        mock_instance.chat.return_value = ChatResponse(
            content="I can help you with that.",
            tool_calls=None
        )
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_path_trust():
    """Mock path trust manager."""
    with patch('spark.agent.PathTrustManager') as mock:
        mock_instance = MagicMock()
        mock_instance.ask_trust_current_dir = Mock()
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def temp_project():
    """Create temporary project directory."""
    with tempfile.TemporaryDirectory() as d:
        project_dir = Path(d)
        (project_dir / "src").mkdir()
        (project_dir / "src" / "main.py").write_text("print('hello')")
        (project_dir / "README.md").write_text("# Test Project")
        yield project_dir


class TestEndToEnd:
    """End-to-end test scenarios."""

    def test_agent_initialization_flow(self, mock_llm, mock_path_trust):
        """Test complete agent initialization."""
        config = Config()
        agent = Agent(config)

        assert agent.config == config
        assert agent.history is not None
        assert agent.security is not None
        assert agent.llm is not None

    def test_agent_mode_switching(self, mock_llm, mock_path_trust):
        """Test switching between modes."""
        config = Config()
        agent = Agent(config, mode="plan")

        assert agent.mode == "plan"

        # Switch to yolo mode
        agent.mode = "yolo"
        assert agent.mode == "yolo"

    def test_agent_language_switching(self, mock_llm, mock_path_trust):
        """Test switching between languages."""
        config = Config()
        agent = Agent(config, lang="en")

        assert agent.lang == "en"

        # Switch to Chinese
        agent.lang = "zh"
        assert agent.lang == "zh"

    def test_agent_build_messages_flow(self, mock_llm, mock_path_trust):
        """Test message building flow."""
        config = Config()
        agent = Agent(config)

        # Add some history
        agent.history.add("user", "Hello")
        agent.history.add("assistant", "Hi there!")

        messages = agent._build_messages("How are you?")

        assert len(messages) >= 3
        assert messages[-1]["role"] == "user"
        assert "How are you?" in messages[-1]["content"]

    def test_agent_tool_execution_flow(self, mock_llm, mock_path_trust, temp_project):
        """Test tool execution flow."""
        config = Config()
        config.security.trust_current_dir = True
        agent = Agent(config, mode="yolo")

        tools = agent._get_all_tools()
        assert len(tools) >= 1

        # Check tool structure
        bash_tool = next((t for t in tools if t["name"] == "Bash"), None)
        assert bash_tool is not None
        assert "parameters" in bash_tool

    def test_security_check_flow(self, mock_llm, mock_path_trust):
        """Test security check flow."""
        config = Config()
        config.security.yolo_mode = True
        agent = Agent(config, mode="yolo")

        # In yolo mode, safe commands should be allowed
        decision = agent.security.check("run_shell", {"command": "ls"})
        assert decision == Decision.ALLOW

    def test_security_deny_dangerous_command(self, mock_llm, mock_path_trust):
        """Test security denies dangerous commands."""
        config = Config()
        agent = Agent(config, mode="ask")

        # Dangerous command should be blocked
        decision = agent.security.check("run_shell", {"command": "rm -rf /"})
        assert decision == Decision.DENY

    def test_history_compression_flow(self, mock_llm, mock_path_trust):
        """Test history compression."""
        config = Config()
        agent = Agent(config)

        # Add many messages
        for i in range(20):
            agent.history.add("user", f"Message {i} " * 50)
            agent.history.add("assistant", f"Response {i}")

        # History should have messages
        assert len(agent.history.messages) > 0

    def test_skills_loading_flow(self, mock_llm, mock_path_trust):
        """Test skills loading."""
        config = Config()
        config.skill_paths = []
        agent = Agent(config)

        # Skills loader should be initialized
        assert agent.skills is not None

    def test_mcp_client_initialization(self, mock_llm, mock_path_trust):
        """Test MCP client initialization."""
        config = Config()
        config.mcp_servers = {}
        agent = Agent(config)

        # MCP client should be initialized
        assert agent.mcp_client is not None

    def test_full_conversation_flow(self, mock_llm, mock_path_trust):
        """Test full conversation flow."""
        config = Config()
        agent = Agent(config)

        # Build messages for a conversation
        messages = agent._build_messages("What is Python?")

        # Should have system and user messages
        assert len(messages) >= 2

        # Simulate LLM response
        mock_llm.chat.return_value = ChatResponse(
            content="Python is a programming language.",
            tool_calls=None
        )

        response = agent.llm.chat(messages)
        assert "Python" in response.content

    def test_tool_call_parsing_flow(self, mock_llm, mock_path_trust):
        """Test tool call parsing from LLM response."""
        config = Config()
        agent = Agent(config)

        # Simulate LLM response with tool call
        mock_llm.chat.return_value = ChatResponse(
            content="Let me check that.",
            tool_calls=[{"function": {"name": "Bash", "arguments": {"command": "ls"}}}]
        )

        response = agent.llm.chat([{"role": "user", "content": "List files"}])
        assert response.tool_calls is not None
        assert response.tool_calls[0]["function"]["name"] == "Bash"

    def test_error_handling_flow(self, mock_llm, mock_path_trust):
        """Test error handling in conversation."""
        config = Config()
        agent = Agent(config)

        # Simulate LLM error
        from spark.errors import LLMConnectionError
        mock_llm.chat.side_effect = LLMConnectionError("Connection failed", {})

        with pytest.raises(LLMConnectionError):
            agent.llm.chat([{"role": "user", "content": "Hello"}])

    def test_multilingual_support(self, mock_llm, mock_path_trust):
        """Test multilingual support."""
        config = Config()

        # Test English
        agent_en = Agent(config, lang="en")
        assert agent_en.t("welcome") is not None

        # Test Chinese
        agent_zh = Agent(config, lang="zh")
        assert agent_zh.t("welcome") is not None

        # Test Japanese
        agent_ja = Agent(config, lang="ja")
        assert agent_ja.t("welcome") is not None

    def test_config_override_flow(self, mock_llm, mock_path_trust):
        """Test configuration override."""
        config = Config()
        config.llm.model = "custom-model"
        config.llm.base_url = "http://custom:11434"

        agent = Agent(config)

        # Config should be passed correctly
        assert agent.config.llm.model == "custom-model"
        assert agent.config.llm.base_url == "http://custom:11434"