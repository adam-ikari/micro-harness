# src/spark/llm.py
"""LLM API adapter for spark - supports Ollama and Anthropic-compatible APIs."""

import re
import json
import logging
from dataclasses import dataclass
from typing import Any
import httpx

from spark.config import LLMConfig
from spark.errors import LLMConnectionError, LLMResponseError, LLMTimeoutError

logger = logging.getLogger(__name__)


@dataclass
class ChatResponse:
    """LLM response wrapper."""
    content: str
    tool_calls: list[dict] | None = None


class OllamaAdapter:
    """LLM adapter supporting Ollama and Anthropic-compatible APIs."""

    def __init__(self, config: LLMConfig):
        self.base_url = config.base_url
        self.model = config.model
        self.num_ctx = config.num_ctx
        self.num_predict = config.num_predict
        self.api_key = config.api_key
        # Small model optimizations
        self.temperature = getattr(config, 'temperature', 0.3)
        self.top_p = getattr(config, 'top_p', 0.9)
        self.repeat_penalty = getattr(config, 'repeat_penalty', 1.1)
        self._client = None

        # Detect API type based on URL or api_key
        self._is_anthropic = "anthropic" in self.base_url.lower() or bool(self.api_key)

    def _get_client(self):
        """Lazy load Ollama client (for Ollama APIs)."""
        if self._client is None:
            import ollama
            self._client = ollama.Client(host=self.base_url)
        return self._client

    def _get_tool_prompt(self, tools: list[dict]) -> str:
        """Generate tool usage prompt optimized for small models.

        Uses few-shot examples to help small models understand format.
        """
        if not tools:
            return ""

        # Minimal prompt with few-shot examples
        prompt = "\nUse: bash(\"cmd\")\n"
        prompt += "Ex: bash(\"ls\")\n"
        prompt += "Ex: bash(\"cat file.py\")\n"
        prompt += "Ex: bash(\"grep pattern *.py\")\n"
        return prompt

    def _parse_tool_calls(self, content: str) -> tuple[str, list[dict] | None]:
        """Parse tool calls from model output.

        Supports formats:
        - bash("command") - primary format
        - Bash("command") - alternative
        - <tool name="Bash">{"command": "pwd"}</tool>
        - ```tool:Bash\n{"command": "pwd"}\n```
        - [Bash: pwd]
        """
        tool_calls = []
        remaining_content = content

        # Pattern 0: bash("command") or Bash("command") - primary format
        pattern0 = r'(?:bash|Bash)\s*\(\s*"([^"]+)"\s*\)'
        for match in re.finditer(pattern0, content):
            command = match.group(1)
            tool_calls.append({
                "function": {
                    "name": "Bash",
                    "arguments": {"command": command}
                }
            })
            remaining_content = remaining_content.replace(match.group(0), "")

        # Pattern 1: <tool name="Name">json</tool>
        pattern1 = r'<tool\s+name=["\']?(\w+)["\']?\s*>([^<]+)</tool>'
        for match in re.finditer(pattern1, content):
            tool_name = match.group(1)
            try:
                args = json.loads(match.group(2).strip())
            except json.JSONDecodeError:
                args = {"command": match.group(2).strip()}
            tool_calls.append({"function": {"name": tool_name, "arguments": args}})
            remaining_content = remaining_content.replace(match.group(0), "")

        # Pattern 2: ```tool:Name\njson\n```
        pattern2 = r'```tool:(\w+)\n([^`]+)```'
        for match in re.finditer(pattern2, content):
            tool_name = match.group(1)
            try:
                args = json.loads(match.group(2).strip())
            except json.JSONDecodeError:
                args = {"command": match.group(2).strip()}
            tool_calls.append({"function": {"name": tool_name, "arguments": args}})
            remaining_content = remaining_content.replace(match.group(0), "")

        # Pattern 3: [ToolName: command] (simple format for small models)
        pattern3 = r'\[(\w+):\s*([^\]]+)\]'
        for match in re.finditer(pattern3, content):
            tool_name = match.group(1)
            tool_calls.append({
                "function": {
                    "name": tool_name,
                    "arguments": {"command": match.group(2).strip()}
                }
            })
            remaining_content = remaining_content.replace(match.group(0), "")

        # Clean up remaining content
        remaining_content = remaining_content.strip()

        return remaining_content, tool_calls if tool_calls else None

    def _call_anthropic(self, messages: list[dict], tools: list[dict] | None = None) -> ChatResponse:
        """Call Anthropic-compatible API."""
        url = self.base_url.rstrip("/")
        if not url.endswith("/v1/messages"):
            url = f"{url}/v1/messages"

        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }

        # Convert messages to Anthropic format
        anthropic_messages = []
        system = None
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                if system:
                    system += "\n\n" + content
                else:
                    system = content
            else:
                anthropic_messages.append({
                    "role": role,
                    "content": content,
                })

        # Add tool prompt to system message (text-based tool calling)
        if tools:
            tool_prompt = self._get_tool_prompt(tools)
            if system:
                system += tool_prompt
            else:
                system = tool_prompt

        payload = {
            "model": self.model,
            "max_tokens": self.num_predict,
            "messages": anthropic_messages,
        }

        if system:
            payload["system"] = system

        try:
            with httpx.Client(timeout=120) as client:
                response = client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
        except httpx.TimeoutException as e:
            logger.error(f"Anthropic API timeout: {e}")
            raise LLMTimeoutError("Anthropic API request timed out", {"url": url})
        except httpx.ConnectError as e:
            logger.error(f"Anthropic API connection error: {e}")
            raise LLMConnectionError("Cannot connect to Anthropic API", {"url": url, "error": str(e)})
        except httpx.HTTPStatusError as e:
            logger.error(f"Anthropic API HTTP error: {e}")
            raise LLMResponseError(f"Anthropic API error: {e.response.status_code}", {"url": url, "status": e.response.status_code})
        except json.JSONDecodeError as e:
            logger.error(f"Anthropic API invalid JSON: {e}")
            raise LLMResponseError("Invalid JSON response from Anthropic API", {"error": str(e)})
        except Exception as e:
            logger.error(f"Anthropic API unexpected error: {e}")
            raise LLMResponseError(f"Unexpected error: {e}", {"error": str(e)})

        # Parse response
        content = ""
        for block in data.get("content", []):
            if block.get("type") == "text":
                content += block.get("text", "")

        # Parse tool calls from content (text-based)
        remaining, tool_calls = self._parse_tool_calls(content)

        return ChatResponse(content=remaining, tool_calls=tool_calls)

    def _call_ollama(self, messages: list[dict], tools: list[dict] | None = None) -> ChatResponse:
        """Call Ollama API."""
        try:
            client = self._get_client()
        except Exception as e:
            logger.error(f"Failed to initialize Ollama client: {e}")
            raise LLMConnectionError("Cannot connect to Ollama", {"base_url": self.base_url, "error": str(e)})

        # Add tool prompt for text-based tool calling
        if tools:
            tool_prompt = self._get_tool_prompt(tools)
            # Prepend to first system message or add one
            for i, msg in enumerate(messages):
                if msg["role"] == "system":
                    messages[i]["content"] += tool_prompt
                    break
            else:
                messages.insert(0, {"role": "system", "content": tool_prompt})

        options = {
            "num_ctx": self.num_ctx,
            "num_predict": self.num_predict,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "repeat_penalty": self.repeat_penalty,
        }

        kwargs = {
            "model": self.model,
            "messages": messages,
            "options": options,
        }

        # Try native tool calling first, fall back to text-based
        try:
            if tools:
                # Simplify tools for Ollama
                simplified = []
                for tool in tools:
                    name = tool.get("name", "")
                    desc = tool.get("description", "")[:80]
                    params = tool.get("parameters", {})
                    if params.get("type") == "object" and "properties" in params:
                        props = params["properties"]
                    else:
                        props = params
                    properties = {}
                    for pname, pdef in props.items():
                        if isinstance(pdef, dict):
                            properties[pname] = {"type": pdef.get("type", "string")}
                        else:
                            properties[pname] = {"type": "string"}
                    simplified.append({
                        "type": "function",
                        "function": {
                            "name": name,
                            "description": desc,
                            "parameters": {
                                "type": "object",
                                "properties": properties,
                            },
                        },
                    })
                kwargs["tools"] = simplified

            response = client.chat(**kwargs)
            message = response.get("message", {})
            content = message.get("content", "")
            tool_calls = message.get("tool_calls", None)

            # If no native tool calls, try text-based parsing
            if not tool_calls:
                remaining, parsed_calls = self._parse_tool_calls(content)
                if parsed_calls:
                    return ChatResponse(content=remaining, tool_calls=parsed_calls)

            return ChatResponse(content=content, tool_calls=tool_calls)
        except Exception as e:
            logger.warning(f"Ollama native tool calling failed, falling back to text-based: {e}")
            # Fall back to text-based
            if "tools" in kwargs:
                del kwargs["tools"]
            try:
                response = client.chat(**kwargs)
                message = response.get("message", {})
                content = message.get("content", "")
                remaining, tool_calls = self._parse_tool_calls(content)
                return ChatResponse(content=remaining, tool_calls=tool_calls)
            except Exception as fallback_error:
                logger.error(f"Ollama fallback also failed: {fallback_error}")
                raise LLMResponseError("Ollama request failed", {"error": str(fallback_error)})

    def estimate_tokens(self, messages: list[dict]) -> int:
        """Estimate token count for messages."""
        total_chars = 0
        for msg in messages:
            content = msg.get("content", "")
            total_chars += len(content)
            total_chars += 15
        return int(total_chars * 0.3)

    def chat(self, messages: list[dict], tools: list[dict] | None = None) -> ChatResponse:
        """Send chat request."""
        if self._is_anthropic:
            return self._call_anthropic(messages, tools)
        else:
            return self._call_ollama(messages, tools)

    def generate_summary(self, messages: list[dict]) -> str:
        """Generate history summary for compression."""
        if not messages:
            return ""

        summary_prompt = "Summarize code changes. Keep: files, functions, fixes.\n\n"
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            if len(content) > 200:
                content = content[:200] + "..."
            summary_prompt += f"{role}: {content}\n"

        response = self.chat(messages=[{"role": "user", "content": summary_prompt}])
        return response.content

    def extract_facts(self, content: str) -> list[str]:
        """Extract key facts from content."""
        if not content:
            return []

        prompt = f"Extract: file paths, function names, decisions. Or NONE.\n\n{content[:500]}"
        response = self.chat(messages=[{"role": "user", "content": prompt}])

        result = response.content
        if result.strip().upper() == "NONE":
            return []

        facts = []
        for line in result.split("\n"):
            line = line.strip()
            if line.startswith("- "):
                facts.append(line[2:])
            elif line:
                facts.append(line)

        return facts[:5]
