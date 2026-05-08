# src/zero_agent/llm.py
"""Ollama API adapter for zero-agent."""

from dataclasses import dataclass
from typing import Any

import ollama

from zero_agent.config import LLMConfig


@dataclass
class ChatResponse:
    """LLM response wrapper."""
    content: str
    tool_calls: list[dict] | None = None


class OllamaAdapter:
    """Ollama API adapter optimized for small models."""

    def __init__(self, config: LLMConfig):
        self.base_url = config.base_url
        self.model = config.model
        self.num_ctx = config.num_ctx
        self.num_predict = config.num_predict
        self._client = None

    def _get_client(self):
        """Lazy load Ollama client."""
        if self._client is None:
            self._client = ollama.Client(host=self.base_url)
        return self._client

    def _simplify_tools(self, tools: list[dict]) -> list[dict]:
        """Simplify tool descriptions for small models.

        Keep only name + description + required params to reduce token usage.
        """
        simplified = []
        for tool in tools:
            simplified.append({
                "type": "function",
                "function": {
                    "name": tool.get("name", ""),
                    "description": tool.get("description", "")[:200],  # Limit description length
                    "parameters": {
                        "type": "object",
                        "properties": tool.get("parameters", {}),
                        "required": list(tool.get("parameters", {}).keys()),
                    },
                },
            })
        return simplified

    def estimate_tokens(self, messages: list[dict]) -> int:
        """Estimate token count for messages.

        Simple estimation: ~0.25 tokens per character (English), ~0.5 for Chinese.
        """
        total_chars = 0
        for msg in messages:
            content = msg.get("content", "")
            total_chars += len(content)
            # Add message format overhead
            total_chars += 20
        return int(total_chars * 0.3)  # Conservative estimate

    def chat(self, messages: list[dict], tools: list[dict] | None = None) -> ChatResponse:
        """Send chat request.

        Args:
            messages: Chat message list
            tools: Available tools list

        Returns:
            ChatResponse: Response with content and tool calls
        """
        client = self._get_client()

        options = {
            "num_ctx": self.num_ctx,
            "num_predict": self.num_predict,
        }

        kwargs = {
            "model": self.model,
            "messages": messages,
            "options": options,
        }

        if tools:
            kwargs["tools"] = self._simplify_tools(tools)

        response = client.chat(**kwargs)

        message = response.get("message", {})
        content = message.get("content", "")
        tool_calls = message.get("tool_calls", None)

        return ChatResponse(content=content, tool_calls=tool_calls)

    def generate_summary(self, messages: list[dict]) -> str:
        """Generate history summary for compression.

        Args:
            messages: Messages to summarize

        Returns:
            str: Summary text
        """
        if not messages:
            return ""

        # Build summary request
        summary_prompt = (
            "Summarize the following conversation briefly. "
            "Keep key information and decisions. "
            "Be concise (under 200 words).\n\n"
        )

        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            summary_prompt += f"{role}: {content}\n"

        client = self._get_client()
        response = client.chat(
            model=self.model,
            messages=[{"role": "user", "content": summary_prompt}],
            options={"num_predict": 300},
        )

        return response.get("message", {}).get("content", "")
