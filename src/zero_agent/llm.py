# src/zero_agent/llm.py
"""Ollama API adapter for zero-agent optimized for small models."""

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

        Ultra-minimal format to save tokens:
        - Description limited to 80 chars
        - Only required parameters
        - No examples or long descriptions
        """
        simplified = []
        for tool in tools:
            # Extract only essential info
            name = tool.get("name", "")
            desc = tool.get("description", "")[:80]  # Very short
            params = tool.get("parameters", {})

            # Build minimal parameter schema
            properties = {}
            required = []
            for pname, pdef in params.items():
                # Only include type and very short description
                properties[pname] = {
                    "type": pdef.get("type", "string"),
                }
                if pdef.get("description"):
                    properties[pname]["description"] = pdef["description"][:50]
                required.append(pname)

            simplified.append({
                "type": "function",
                "function": {
                    "name": name,
                    "description": desc,
                    "parameters": {
                        "type": "object",
                        "properties": properties,
                        "required": required,
                    },
                },
            })
        return simplified

    def estimate_tokens(self, messages: list[dict]) -> int:
        """Estimate token count for messages.

        Optimized estimation for mixed content:
        - English: ~0.25 tokens/char
        - Code: ~0.3 tokens/char
        - Chinese: ~0.5 tokens/char
        """
        total_chars = 0
        for msg in messages:
            content = msg.get("content", "")
            total_chars += len(content)
            # Add message format overhead
            total_chars += 15
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

        Optimized for small models with minimal prompt.
        """
        if not messages:
            return ""

        # Build minimal summary request
        summary_prompt = "Summarize code changes. Keep: files, functions, fixes.\n\n"

        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            # Truncate long messages
            if len(content) > 200:
                content = content[:200] + "..."
            summary_prompt += f"{role}: {content}\n"

        client = self._get_client()
        response = client.chat(
            model=self.model,
            messages=[{"role": "user", "content": summary_prompt}],
            options={"num_predict": 200},  # Short summary
        )

        return response.get("message", {}).get("content", "")

    def extract_facts(self, content: str) -> list[str]:
        """Extract key facts from content.

        Optimized for programming context.
        """
        if not content:
            return []

        prompt = f"Extract: file paths, function names, decisions. Or NONE.\n\n{content[:500]}"

        client = self._get_client()
        response = client.chat(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            options={"num_predict": 100},
        )

        result = response.get("message", {}).get("content", "")
        if result.strip().upper() == "NONE":
            return []

        # Parse facts
        facts = []
        for line in result.split("\n"):
            line = line.strip()
            if line.startswith("- "):
                facts.append(line[2:])
            elif line:
                facts.append(line)

        return facts[:5]  # Limit to 5 facts
