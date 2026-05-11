# tests/test_llm_adapter.py
"""Tests for LLM adapter."""

import pytest
from spark.llm import OllamaAdapter
from spark.config import LLMConfig


class TestToolPrompt:
    """Tests for tool prompt generation."""

    def test_get_tool_prompt_empty(self):
        """Test tool prompt with no tools."""
        config = LLMConfig()
        adapter = OllamaAdapter(config)
        prompt = adapter._get_tool_prompt([])
        assert prompt == ""

    def test_get_tool_prompt_single(self):
        """Test tool prompt with single tool."""
        config = LLMConfig()
        adapter = OllamaAdapter(config)
        tools = [{"name": "Bash", "description": "Run command", "parameters": {}}]
        prompt = adapter._get_tool_prompt(tools)
        assert "Bash" in prompt
        assert "Run command" in prompt

    def test_get_tool_prompt_multiple(self):
        """Test tool prompt with multiple tools."""
        config = LLMConfig()
        adapter = OllamaAdapter(config)
        tools = [
            {"name": "Bash", "description": "Run command", "parameters": {}},
            {"name": "Read", "description": "Read file", "parameters": {}},
        ]
        prompt = adapter._get_tool_prompt(tools)
        assert "Bash" in prompt
        assert "Read" in prompt


class TestToolCallParsing:
    """Tests for tool call parsing from text."""

    def test_parse_xml_format(self):
        """Test parsing <tool> XML format."""
        config = LLMConfig()
        adapter = OllamaAdapter(config)
        content = 'Some text <tool name="Bash">{"command": "pwd"}</tool> more text'
        remaining, calls = adapter._parse_tool_calls(content)
        assert calls is not None
        assert len(calls) == 1
        assert calls[0]["function"]["name"] == "Bash"
        assert calls[0]["function"]["arguments"]["command"] == "pwd"

    def test_parse_code_block_format(self):
        """Test parsing ```tool:Name format."""
        config = LLMConfig()
        adapter = OllamaAdapter(config)
        content = '```tool:Bash\n{"command": "ls"}\n```'
        remaining, calls = adapter._parse_tool_calls(content)
        assert calls is not None
        assert len(calls) == 1
        assert calls[0]["function"]["name"] == "Bash"

    def test_parse_bracket_format(self):
        """Test parsing [ToolName: command] format."""
        config = LLMConfig()
        adapter = OllamaAdapter(config)
        content = "Let me run [Bash: pwd] for you"
        remaining, calls = adapter._parse_tool_calls(content)
        assert calls is not None
        assert len(calls) == 1
        assert calls[0]["function"]["name"] == "Bash"
        assert calls[0]["function"]["arguments"]["command"] == "pwd"

    def test_parse_multiple_calls(self):
        """Test parsing multiple tool calls."""
        config = LLMConfig()
        adapter = OllamaAdapter(config)
        content = '[Bash: pwd] and [Bash: ls]'
        remaining, calls = adapter._parse_tool_calls(content)
        assert calls is not None
        assert len(calls) == 2

    def test_parse_no_calls(self):
        """Test content with no tool calls."""
        config = LLMConfig()
        adapter = OllamaAdapter(config)
        content = "Just regular text without any tool calls"
        remaining, calls = adapter._parse_tool_calls(content)
        assert calls is None


class TestTokenEstimation:
    """Tests for token estimation."""

    def test_estimate_empty(self):
        """Test estimation with empty messages."""
        config = LLMConfig()
        adapter = OllamaAdapter(config)
        tokens = adapter.estimate_tokens([])
        assert tokens == 0

    def test_estimate_single(self):
        """Test estimation with single message."""
        config = LLMConfig()
        adapter = OllamaAdapter(config)
        messages = [{"role": "user", "content": "hello world"}]
        tokens = adapter.estimate_tokens(messages)
        assert tokens > 0
        # Should be roughly proportional to content length
        assert tokens < 50  # "hello world" + overhead
