# src/spark/errors.py
"""Custom exceptions for Spark."""

from typing import Optional


class SparkError(Exception):
    """Base exception for all Spark errors."""

    def __init__(self, message: str, details: Optional[dict] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} - {self.details}"
        return self.message


class LLMError(SparkError):
    """LLM-related errors."""

    pass


class LLMConnectionError(LLMError):
    """Cannot connect to LLM service."""

    pass


class LLMResponseError(LLMError):
    """Invalid response from LLM."""

    pass


class LLMTimeoutError(LLMError):
    """LLM request timed out."""

    pass


class ToolError(SparkError):
    """Tool execution errors."""

    pass


class ToolNotFoundError(ToolError):
    """Requested tool does not exist."""

    pass


class ToolExecutionError(ToolError):
    """Tool execution failed."""

    pass


class SecurityError(SparkError):
    """Security-related errors."""

    pass


class PathNotTrustedError(SecurityError):
    """Path is not trusted for the requested operation."""

    pass


class CommandBlockedError(SecurityError):
    """Command is blocked by security policy."""

    pass


class PermissionDeniedError(SecurityError):
    """Permission denied for operation."""

    pass


class ConfigError(SparkError):
    """Configuration errors."""

    pass


class ConfigNotFoundError(ConfigError):
    """Configuration file not found."""

    pass


class ConfigValidationError(ConfigError):
    """Configuration validation failed."""

    pass


class HistoryError(SparkError):
    """History management errors."""

    pass


class HistoryCompressionError(HistoryError):
    """Failed to compress history."""

    pass


class MCPError(SparkError):
    """MCP-related errors."""

    pass


class MCPConnectionError(MCPError):
    """Cannot connect to MCP server."""

    pass


class MCPToolError(MCPError):
    """MCP tool execution failed."""

    pass


class SkillError(SparkError):
    """Skill-related errors."""

    pass


class SkillLoadError(SkillError):
    """Failed to load skill."""

    pass


class SkillExecutionError(SkillError):
    """Skill execution failed."""

    pass


def format_error(error: Exception, lang: str = "en") -> str:
    """Format error message for display.

    Args:
        error: Exception to format
        lang: Language for message (en, zh, ja)

    Returns:
        Formatted error message
    """
    messages = {
        "en": {
            "llm_connection": "Cannot connect to LLM service. Check if Ollama is running.",
            "llm_response": "Invalid response from LLM.",
            "llm_timeout": "LLM request timed out. Try again.",
            "tool_not_found": "Tool '{}' not found.",
            "tool_execution": "Tool execution failed: {}",
            "path_not_trusted": "Path '{}' not trusted for {} operation.",
            "command_blocked": "Command '{}' blocked by security policy.",
            "permission_denied": "Permission denied: {}",
        },
        "zh": {
            "llm_connection": "无法连接 LLM 服务。请检查 Ollama 是否运行。",
            "llm_response": "LLM 返回无效响应。",
            "llm_timeout": "LLM 请求超时。请重试。",
            "tool_not_found": "工具 '{}' 不存在。",
            "tool_execution": "工具执行失败: {}",
            "path_not_trusted": "路径 '{}' 未被信任，无法执行 {} 操作。",
            "command_blocked": "命令 '{}' 被安全策略阻止。",
            "permission_denied": "权限被拒绝: {}",
        },
        "ja": {
            "llm_connection": "LLMサービスに接続できません。Ollamaが実行中か確認してください。",
            "llm_response": "LLMからの無効な応答。",
            "llm_timeout": "LLMリクエストがタイムアウトしました。再試行してください。",
            "tool_not_found": "ツール '{}' が見つかりません。",
            "tool_execution": "ツール実行エラー: {}",
            "path_not_trusted": "パス '{}' は{}操作に対して信頼されていません。",
            "command_blocked": "コマンド '{}' はセキュリティポリシーによりブロックされました。",
            "permission_denied": "権限が拒否されました: {}",
        },
    }

    lang_messages = messages.get(lang, messages["en"])

    if isinstance(error, LLMConnectionError):
        return lang_messages["llm_connection"]
    elif isinstance(error, LLMResponseError):
        return lang_messages["llm_response"]
    elif isinstance(error, LLMTimeoutError):
        return lang_messages["llm_timeout"]
    elif isinstance(error, ToolNotFoundError):
        return lang_messages["tool_not_found"].format(error.details.get("tool", "unknown"))
    elif isinstance(error, ToolExecutionError):
        return lang_messages["tool_execution"].format(error.message)
    elif isinstance(error, PathNotTrustedError):
        return lang_messages["path_not_trusted"].format(
            error.details.get("path", "unknown"),
            error.details.get("operation", "unknown")
        )
    elif isinstance(error, CommandBlockedError):
        return lang_messages["command_blocked"].format(error.details.get("command", "unknown"))
    elif isinstance(error, PermissionDeniedError):
        return lang_messages["permission_denied"].format(error.message)
    elif isinstance(error, SparkError):
        return str(error)
    else:
        return f"Error: {error}"
