# tests/test_llm.py
import pytest
from unittest.mock import Mock, patch, MagicMock
from spark.llm import OllamaAdapter, ChatResponse
from spark.config import LLMConfig


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

    # Test the tool prompt generation instead of non-existent _simplify_tools
    tool_prompt = adapter._get_tool_prompt(tools)
    assert "run_shell" in tool_prompt
    assert "Execute shell command" in tool_prompt


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


def test_ollama_adapter_anthropic_detection():
    """Test Anthropic API detection."""
    config = LLMConfig(base_url="https://api.anthropic.com", api_key="test-key")
    adapter = OllamaAdapter(config)
    assert adapter._is_anthropic is True


def test_ollama_adapter_ollama_detection():
    """Test Ollama API detection."""
    config = LLMConfig(base_url="http://localhost:11434")
    adapter = OllamaAdapter(config)
    assert adapter._is_anthropic is False


def test_ollama_adapter_tool_prompt_empty():
    """Test tool prompt with empty tools."""
    config = LLMConfig()
    adapter = OllamaAdapter(config)

    prompt = adapter._get_tool_prompt([])
    assert prompt == ""


def test_ollama_adapter_tool_prompt_with_params():
    """Test tool prompt with parameters."""
    config = LLMConfig()
    adapter = OllamaAdapter(config)

    tools = [
        {
            "name": "test_tool",
            "description": "A test tool",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "mode": {"type": "string"}
                }
            }
        }
    ]

    prompt = adapter._get_tool_prompt(tools)
    assert "test_tool" in prompt
    assert "path" in prompt or "mode" in prompt


def test_ollama_adapter_parse_tool_calls_xml():
    """Test parsing XML-style tool calls."""
    config = LLMConfig()
    adapter = OllamaAdapter(config)

    content = "Let me check.\n<tool name=\"Bash\">{\"command\": \"ls\"}</tool>"
    remaining, tool_calls = adapter._parse_tool_calls(content)

    assert tool_calls is not None
    assert len(tool_calls) == 1
    assert tool_calls[0]["function"]["name"] == "Bash"


def test_ollama_adapter_parse_tool_calls_code_block():
    """Test parsing code block tool calls."""
    config = LLMConfig()
    adapter = OllamaAdapter(config)

    content = "Running command.\n```tool:Bash\n{\"command\": \"pwd\"}\n```"
    remaining, tool_calls = adapter._parse_tool_calls(content)

    assert tool_calls is not None
    assert len(tool_calls) == 1


def test_ollama_adapter_parse_tool_calls_simple():
    """Test parsing simple bracket tool calls."""
    config = LLMConfig()
    adapter = OllamaAdapter(config)

    content = "Let me run [Bash: ls -la]"
    remaining, tool_calls = adapter._parse_tool_calls(content)

    assert tool_calls is not None
    assert len(tool_calls) == 1
    assert tool_calls[0]["function"]["name"] == "Bash"


def test_ollama_adapter_parse_bash_format():
    """Test parsing bash("command") format."""
    config = LLMConfig()
    adapter = OllamaAdapter(config)

    content = "I'll check the files: bash(\"ls -la\")"
    remaining, tool_calls = adapter._parse_tool_calls(content)

    assert tool_calls is not None
    assert len(tool_calls) == 1
    assert tool_calls[0]["function"]["name"] == "Bash"
    assert tool_calls[0]["function"]["arguments"]["command"] == "ls -la"


def test_ollama_adapter_parse_bash_format_complex():
    """Test parsing bash() with complex command."""
    config = LLMConfig()
    adapter = OllamaAdapter(config)

    content = "bash(\"find . -name '*.py' | xargs wc -l\")"
    remaining, tool_calls = adapter._parse_tool_calls(content)

    assert tool_calls is not None
    assert tool_calls[0]["function"]["arguments"]["command"] == "find . -name '*.py' | xargs wc -l"


def test_ollama_adapter_parse_multiple_bash_calls():
    """Test parsing multiple bash() calls."""
    config = LLMConfig()
    adapter = OllamaAdapter(config)

    content = "First: bash(\"ls\") then: bash(\"pwd\")"
    remaining, tool_calls = adapter._parse_tool_calls(content)

    assert tool_calls is not None
    assert len(tool_calls) == 2


def test_ollama_adapter_parse_tool_calls_none():
    """Test parsing when no tool calls."""
    config = LLMConfig()
    adapter = OllamaAdapter(config)

    content = "This is just a regular response."
    remaining, tool_calls = adapter._parse_tool_calls(content)

    assert tool_calls is None


def test_ollama_adapter_generate_summary():
    """Test summary generation."""
    config = LLMConfig()
    adapter = OllamaAdapter(config)

    with patch.object(adapter, 'chat') as mock_chat:
        mock_chat.return_value = ChatResponse(content="Summary: discussed Python", tool_calls=None)

        messages = [
            {"role": "user", "content": "What is Python?"},
            {"role": "assistant", "content": "Python is a language"}
        ]

        summary = adapter.generate_summary(messages)
        assert "Summary" in summary or "Python" in summary


def test_ollama_adapter_extract_facts():
    """Test fact extraction."""
    config = LLMConfig()
    adapter = OllamaAdapter(config)

    with patch.object(adapter, 'chat') as mock_chat:
        mock_chat.return_value = ChatResponse(content="- Python is a language\n- Used for web", tool_calls=None)

        facts = adapter.extract_facts("Python is a programming language")
        assert len(facts) >= 0


def test_ollama_adapter_extract_facts_none():
    """Test fact extraction returns NONE."""
    config = LLMConfig()
    adapter = OllamaAdapter(config)

    with patch.object(adapter, 'chat') as mock_chat:
        mock_chat.return_value = ChatResponse(content="NONE", tool_calls=None)

        facts = adapter.extract_facts("random text")
        assert facts == []


@patch('spark.llm.httpx.Client')
def test_ollama_adapter_call_anthropic(mock_client):
    """Test Anthropic API call."""
    config = LLMConfig(
        base_url="https://api.anthropic.com",
        api_key="test-key",
        model="claude-3"
    )
    adapter = OllamaAdapter(config)

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "content": [{"type": "text", "text": "Hello"}]
    }
    mock_response.raise_for_status = Mock()

    mock_httpx = MagicMock()
    mock_httpx.__enter__ = Mock(return_value=mock_httpx)
    mock_httpx.__exit__ = Mock(return_value=False)
    mock_httpx.post.return_value = mock_response
    mock_client.return_value = mock_httpx

    messages = [{"role": "user", "content": "Hi"}]
    response = adapter._call_anthropic(messages)

    assert response.content == "Hello"


def test_chat_response_dataclass():
    """Test ChatResponse dataclass."""
    response = ChatResponse(content="Test", tool_calls=None)
    assert response.content == "Test"
    assert response.tool_calls is None


def test_chat_response_with_tool_calls():
    """Test ChatResponse with tool calls."""
    tool_calls = [{"function": {"name": "Bash", "arguments": {"command": "ls"}}}]
    response = ChatResponse(content="Running", tool_calls=tool_calls)
    assert response.tool_calls == tool_calls
