# src/spark/prompts.py
"""Optimized prompts for small models in programming scenarios."""

import re
from typing import Optional

# Minimal system prompts per mode (optimized for small models)
SYSTEM_PROMPTS = {
    "plan": "Analyze code. Read-only. No execution.",
    "ask": "Code helper. Ask before write.",
    "yolo": "Code helper. Execute freely.",
}

# Default fallback
DEFAULT_SYSTEM = "Code helper."

# Few-shot examples for tool calling (critical for small models)
TOOL_EXAMPLES = """
Examples:
User: list files
You: bash("ls")

User: read main.py
You: bash("cat main.py")

User: find python files
You: bash("find . -name '*.py'")

User: search for error in logs
You: bash("grep error *.log")

User: count lines in file
You: bash("wc -l file.txt")
"""

# Programming context hints (minimal)
CONTEXT_HINTS = {
    "debug": "Find bugs. Suggest fixes.",
    "write": "Write clean code.",
    "refactor": "Improve structure.",
    "test": "Write tests.",
    "explain": "Explain simply.",
}

# Compression prompts (minimal)
COMPRESSION_PROMPT = "Summarize: files, functions, fixes."

EXTRACTION_PROMPT = "Extract: files, functions. Or NONE."

# Programming keywords for context detection
PROGRAMMING_KEYWORDS = {
    "debug": ["bug", "error", "fix", "crash", "exception", "traceback", "fail"],
    "write": ["create", "add", "implement", "write", "new feature"],
    "refactor": ["refactor", "clean", "improve", "optimize", "simplify"],
    "test": ["test", "spec", "coverage", "pytest", "unittest", "jest"],
    "explain": ["explain", "what", "how", "why", "understand"],
}

# File extension patterns
FILE_PATTERNS = [
    r'\.[a-z]{1,4}$',  # File extensions
    r'[/\\]',  # Paths
    r'def\s+\w+',  # Function definitions
    r'class\s+\w+',  # Class definitions
    r'import\s+',  # Imports
    r'from\s+\w+',  # From imports
]


def detect_context(user_input: str) -> Optional[str]:
    """Detect programming context from user input.

    Args:
        user_input: User's input text

    Returns:
        Optional[str]: Detected context or None
    """
    lower = user_input.lower()

    # Check for file/code patterns first
    for pattern in FILE_PATTERNS:
        if re.search(pattern, user_input):
            # Has code/file reference, determine action
            break

    # Check keywords
    for context, keywords in PROGRAMMING_KEYWORDS.items():
        for kw in keywords:
            if kw in lower:
                return context

    return None


def get_system_prompt(mode: str, lang: str = "en") -> str:
    """Get minimal system prompt for mode.

    Args:
        mode: Current mode (plan/ask/yolo)
        lang: Language (en/zh/ja)

    Returns:
        str: Minimal system prompt
    """
    return SYSTEM_PROMPTS.get(mode, DEFAULT_SYSTEM)


def get_context_hint(context: str) -> str:
    """Get context-specific hint.

    Args:
        context: Programming context

    Returns:
        str: Context hint
    """
    return CONTEXT_HINTS.get(context, "")


def get_tool_hint(tool_name: str) -> str:
    """Get minimal tool usage hint.

    Args:
        tool_name: Tool name

    Returns:
        str: Short hint or empty
    """
    return TOOL_HINTS.get(tool_name, "")


def build_compact_prompt(messages: list[dict], max_tokens: int = 4000) -> list[dict]:
    """Build compact message list within token budget.

    Args:
        messages: Original messages
        max_tokens: Token budget

    Returns:
        list[dict]: Compact messages within budget
    """
    if not messages:
        return []

    # Estimate tokens (4 chars ≈ 1 token)
    def estimate(msg: dict) -> int:
        return len(msg.get("content", "")) // 4 + 10

    total = 0
    result = []

    # Always keep system message
    if messages and messages[0].get("role") == "system":
        result.append(messages[0])
        total += estimate(messages[0])
        messages = messages[1:]

    # Keep recent messages within budget
    for msg in reversed(messages):
        tokens = estimate(msg)
        if total + tokens > max_tokens:
            break
        result.insert(1, msg)  # Insert after system
        total += tokens

    return result


def build_context_aware_prompt(mode: str, user_input: str) -> str:
    """Build minimal context-aware system prompt.

    Args:
        mode: Current mode
        user_input: User's input

    Returns:
        str: Optimized system prompt
    """
    base = get_system_prompt(mode)
    context = detect_context(user_input)

    if context:
        hint = get_context_hint(context)
        return f"{base} {hint}"

    return base
