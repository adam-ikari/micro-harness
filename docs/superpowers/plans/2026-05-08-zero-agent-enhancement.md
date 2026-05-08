# Zero Agent Enhancement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enhance zero-agent with path trust system, memory persistence, skill auto-trigger, simplified config, and CLI improvements.

**Architecture:** Modular security layer with path trust manager, memory system with Markdown persistence, skill matching with LLM judgment, two-tier configuration.

**Tech Stack:** Python 3.11+, Textual (TUI), Ollama (LLM), PyYAML (config)

---

## Design Decisions Summary

### Path Trust System
- Trust only current directory, no persistence
- Ask on first startup if trust current dir
- Path behavior by mode: Plan (read only), Ask (read allowed, write confirm), Yolo (read/write allowed, high-risk confirm)

### Memory System
- Extract important content during compression
- Persist as Markdown
- Three update triggers: compression append, session end, manual save
- Semantic deduplication
- Layered loading: summary always, details on-demand

### Skills Enhancement
- Hybrid trigger: auto if trigger field exists, else manual
- LLM judges best match
- Combined approach: rule filter + LLM precise judgment

### Configuration
- Two tiers: user global (~/.zero-agent/) + project (./.zero-agent/)
- Project config auto-created silently
- New CLI params: --trust, --memory

### Language
- Affects prompt text + LLM interaction language
- Switch takes effect immediately

---

## P0: Path Trust System

### Task 1: Create PathTrustManager Module

**Files:**
- Create: `src/zero_agent/security/path_trust.py`

- [ ] **Step 1: Implement PathTrustManager class**

```python
# src/zero_agent/security/path_trust.py
"""Path trust management for zero-agent."""

import os
from pathlib import Path
from typing import Optional

from zero_agent.security import Decision


class PathTrustManager:
    """Manage trusted paths for security checks.

    Only current directory can be trusted.
    Trust is not persisted - asked each session.
    """

    def __init__(self, trust_current_dir: bool = False):
        self.trusted_paths: set[str] = set()
        self.current_dir = os.getcwd()
        self._trust_current_dir = trust_current_dir

    def ask_trust_current_dir(self) -> bool:
        """Ask user if they trust current directory.

        Returns:
            bool: True if user trusts, False otherwise
        """
        print(f"\n是否信任当前目录? {self.current_dir}")
        print("[y/N]: ", end="")
        response = input().strip().lower()
        if response == "y":
            self.trusted_paths.add(self.current_dir)
            return True
        return False

    def is_trusted(self, path: str) -> bool:
        """Check if path is trusted.

        Args:
            path: Path to check

        Returns:
            bool: True if path is trusted
        """
        abs_path = os.path.abspath(path)
        for trusted in self.trusted_paths:
            if abs_path.startswith(trusted):
                return True
        return False

    def check_path_permission(self, path: str, operation: str, mode: str) -> Decision:
        """Check path permission based on mode.

        Args:
            path: Path being accessed
            operation: 'read' or 'write'
            mode: 'plan', 'ask', or 'yolo'

        Returns:
            Decision: ALLOW, DENY, or CONFIRM
        """
        # Plan mode: read allowed, write denied
        if mode == "plan":
            if operation == "read":
                return Decision.ALLOW
            return Decision.DENY

        # Ask mode: read allowed, write needs confirm if not trusted
        if mode == "ask":
            if operation == "read":
                return Decision.ALLOW
            if self.is_trusted(path):
                return Decision.ALLOW
            return Decision.CONFIRM

        # Yolo mode: all allowed, but high-risk still needs confirm
        if mode == "yolo":
            if self.is_trusted(path):
                return Decision.ALLOW
            # Non-trusted path in yolo mode still needs confirm for writes
            if operation == "write":
                return Decision.CONFIRM
            return Decision.ALLOW

        return Decision.CONFIRM

    def get_path_from_command(self, command: str) -> list[tuple[str, str]]:
        """Extract paths and operations from command.

        Args:
            command: Shell command string

        Returns:
            List of (path, operation) tuples
        """
        # This will be implemented in path_parser.py
        pass
```

- [ ] **Step 2: Commit**

```bash
git add src/zero_agent/security/path_trust.py
git commit -m "feat: add PathTrustManager for path security"
```

---

### Task 2: Create Path Parser Module

**Files:**
- Create: `src/zero_agent/security/path_parser.py`

- [ ] **Step 1: Implement PathParser class with rule matching**

```python
# src/zero_agent/security/path_parser.py
"""Parse paths from shell commands."""

import os
import re
from typing import Optional


class PathParseCache:
    """Cache for path parsing results."""

    def __init__(self, max_size: int = 100):
        self.cache: dict[str, dict] = {}
        self.max_size = max_size

    def get(self, command: str) -> Optional[dict]:
        """Get cached parse result."""
        return self.cache.get(command)

    def set(self, command: str, result: dict) -> None:
        """Cache parse result."""
        if len(self.cache) >= self.max_size:
            # Remove oldest entry
            oldest = next(iter(self.cache))
            del self.cache[oldest]
        self.cache[command] = result


class PathParser:
    """Extract paths and operations from shell commands.

    Uses rule matching for common commands, LLM for complex cases.
    """

    # Command patterns: {command: [operation, arg_position]}
    # operation: 'read' or 'write'
    # arg_position: argument index containing path, None for optional, -1 for last
    COMMAND_PATTERNS = {
        # File reading
        "cat": ("read", 0),
        "less": ("read", 0),
        "more": ("read", 0),
        "head": ("read", 0),
        "tail": ("read", 0),

        # File writing
        "vim": ("write", 0),
        "nano": ("write", 0),
        "vi": ("write", 0),
        "rm": ("write", 0),
        "mkdir": ("write", 0),
        "touch": ("write", 0),
        "mv": ("write", 0),
        "cp": ("write", 0),  # Destination is write

        # Directory operations
        "ls": ("read", None),  # Optional path arg
        "cd": ("read", 0),
        "find": ("read", 0),

        # Git (usually safe in project dir)
        "git": ("read", None),
    }

    # Redirect patterns
    REDIRECT_PATTERNS = [
        (r">\s*(\S+)", "write"),      # > file
        (r">>\s*(\S+)", "write"),     # >> file
        (r"<\s*(\S+)", "read"),       # < file
    ]

    def __init__(self, llm=None):
        self.llm = llm
        self.cache = PathParseCache()

    def parse(self, command: str) -> list[tuple[str, str]]:
        """Parse command to extract paths and operations.

        Args:
            command: Shell command string

        Returns:
            List of (path, operation) tuples
        """
        # Check cache first
        cached = self.cache.get(command)
        if cached:
            return cached.get("results", [])

        # Try rule matching first
        results = self._parse_by_rules(command)

        # If rule matching failed and LLM available, use LLM
        if not results and self.llm:
            results = self._parse_by_llm(command)

        # Cache results
        self.cache.set(command, {"results": results})

        return results

    def _parse_by_rules(self, command: str) -> list[tuple[str, str]]:
        """Parse using predefined rules."""
        results = []

        # Check for redirects first
        for pattern, operation in self.REDIRECT_PATTERNS:
            matches = re.findall(pattern, command)
            for match in matches:
                results.append((match, operation))

        # Parse command and arguments
        parts = command.split()
        if not parts:
            return results

        cmd = parts[0]

        # Check if command is in patterns
        if cmd in self.COMMAND_PATTERNS:
            operation, arg_pos = self.COMMAND_PATTERNS[cmd]

            if arg_pos is None:
                # Optional path argument
                if len(parts) > 1 and not parts[1].startswith("-"):
                    path = parts[1]
                    results.append((path, operation))
            elif arg_pos == -1:
                # Last argument
                if parts:
                    path = parts[-1]
                    results.append((path, operation))
            elif arg_pos < len(parts):
                # Specific position
                path = parts[arg_pos]
                results.append((path, operation))

        return results

    def _parse_by_llm(self, command: str) -> list[tuple[str, str]]:
        """Parse using LLM for complex commands."""
        if not self.llm:
            return []

        prompt = f"""Analyze this shell command and extract file paths and their operations.

Command: {command}

For each path, determine if it's a 'read' or 'write' operation.
- read: viewing, reading, listing files
- write: creating, modifying, deleting files

Output format (one per line):
path|operation

Example output:
/home/user/file.txt|read
/home/user/output.txt|write

If no paths found, output: NONE"""

        try:
            response = self.llm.chat([{"role": "user", "content": prompt}])
            content = response.content.strip()

            if content == "NONE":
                return []

            results = []
            for line in content.split("\n"):
                if "|" in line:
                    path, operation = line.split("|")
                    path = path.strip()
                    operation = operation.strip().lower()
                    if operation in ("read", "write"):
                        results.append((path, operation))

            return results
        except Exception:
            return []
```

- [ ] **Step 2: Commit**

```bash
git add src/zero_agent/security/path_parser.py
git commit -m "feat: add PathParser for extracting paths from shell commands"
```

---

### Task 3: Integrate Path Trust into Security Module

**Files:**
- Modify: `src/zero_agent/security/__init__.py`
- Modify: `src/zero_agent/config.py`

- [ ] **Step 1: Update security __init__.py**

```python
# Add to src/zero_agent/security/__init__.py
from zero_agent.security.path_trust import PathTrustManager
from zero_agent.security.path_parser import PathParser

__all__ = [
    "Decision",
    "SecurityManager",
    "PermissionManager",
    "RiskDetector",
    "PathTrustManager",
    "PathParser",
]
```

- [ ] **Step 2: Add path trust config to config.py**

Add to SecurityConfig dataclass:
```python
@dataclass
class SecurityConfig:
    permissions: dict = field(default_factory=lambda: {"run_shell": "confirm"})
    yolo_mode: bool = False
    shell_timeout: int = 30
    blocked_commands: list = field(default_factory=lambda: ["rm -rf /", "mkfs", "dd if="])
    confirm_patterns: list = field(default_factory=lambda: ["rm", "sudo", "git push", "chmod"])
    # New fields
    trust_current_dir: bool = False
    ask_trust_on_startup: bool = True
```

- [ ] **Step 3: Commit**

```bash
git add src/zero_agent/security/__init__.py src/zero_agent/config.py
git commit -m "feat: integrate path trust into security module"
```

---

### Task 4: Integrate Path Trust into Agent

**Files:**
- Modify: `src/zero_agent/agent.py`

- [ ] **Step 1: Add PathTrustManager to Agent.__init__**

```python
# In Agent.__init__, add:
from zero_agent.security import PathTrustManager, PathParser

self.path_trust = PathTrustManager()
self.path_parser = PathParser(self.llm)

# Ask about trusting current dir on startup
if config.security.ask_trust_on_startup:
    self.path_trust.ask_trust_current_dir()
```

- [ ] **Step 2: Update _handle_tool_call to check paths**

```python
def _handle_tool_call(self, tool_name: str, args: dict) -> str:
    """Handle tool call."""
    if tool_name == "run_shell":
        command = args.get("command", "")

        # Parse paths from command
        paths = self.path_parser.parse(command)

        # Check each path
        for path, operation in paths:
            decision = self.path_trust.check_path_permission(path, operation, self.mode)
            if decision == Decision.DENY:
                if self.mode == "plan" and operation == "write":
                    switch = input(self.t("write_blocked"))
                    if switch.lower() == "y":
                        self.mode = "ask"
                        print(self.t("switched_mode", self.mode))
                    else:
                        return self.t("error_write_plan")
                else:
                    return self.t("error_denied", tool_name)

            if decision == Decision.CONFIRM:
                confirm = input(f"Path {path} not trusted. Allow {operation}? [y/N]: ")
                if confirm.lower() != "y":
                    return self.t("error_cancelled")

        # Original security check
        decision = self._get_tool_decision(tool_name, args)
        # ... rest of original code
```

- [ ] **Step 3: Commit**

```bash
git add src/zero_agent/agent.py
git commit -m "feat: integrate path trust checking into agent"
```

---

### Task 5: Integrate Path Trust into TUI

**Files:**
- Modify: `src/zero_agent/tui/app.py`

- [ ] **Step 1: Add PathTrustManager to TUI app**

Similar integration as Agent, but using TUI dialogs for prompts.

- [ ] **Step 2: Commit**

```bash
git add src/zero_agent/tui/app.py
git commit -m "feat: integrate path trust into TUI"
```

---

## P1: Memory System

### Task 6: Create Memory Manager Module

**Files:**
- Create: `src/zero_agent/memory/manager.py`
- Create: `src/zero_agent/memory/__init__.py`

- [ ] **Step 1: Implement MemoryManager class**

```python
# src/zero_agent/memory/manager.py
"""Memory management with Markdown persistence."""

import os
from datetime import datetime
from pathlib import Path
from typing import Optional


class MemoryManager:
    """Manage conversation memory with Markdown persistence.

    Features:
    - Extract important content during compression
    - Persist as Markdown
    - Semantic deduplication
    - Layered loading
    """

    def __init__(self, memory_path: str = "./.zero-agent/memory.md"):
        self.memory_path = Path(memory_path)
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize file if not exists
        if not self.memory_path.exists():
            self._init_memory_file()

    def _init_memory_file(self):
        """Initialize empty memory file."""
        content = """# Zero Agent Memory

## Summary
(Always loaded - key facts and decisions)

## Details
(Loaded on demand - full conversation history)

"""
        self.memory_path.write_text(content)

    def load_summary(self) -> str:
        """Load summary section (always loaded)."""
        content = self.memory_path.read_text()

        # Extract summary section
        summary_match = re.search(r"## Summary\n(.*?)(?=\n## |$)", content, re.DOTALL)
        if summary_match:
            return summary_match.group(1).strip()
        return ""

    def load_details(self) -> str:
        """Load details section (on demand)."""
        content = self.memory_path.read_text()

        # Extract details section
        details_match = re.search(r"## Details\n(.*?)$", content, re.DOTALL)
        if details_match:
            return details_match.group(1).strip()
        return ""

    def append_to_summary(self, content: str):
        """Append to summary section."""
        # Implementation
        pass

    def append_to_details(self, content: str):
        """Append to details section."""
        # Implementation
        pass

    def deduplicate(self, llm):
        """Semantic deduplication using LLM."""
        # Implementation
        pass

    def save_session(self, session_summary: str):
        """Save session summary on exit."""
        # Implementation
        pass
```

- [ ] **Step 2: Commit**

```bash
git add src/zero_agent/memory/
git commit -m "feat: add MemoryManager for Markdown persistence"
```

---

### Task 7: Integrate Memory into History Compression

**Files:**
- Modify: `src/zero_agent/history.py`

- [ ] **Step 1: Update compress method to extract important content**

- [ ] **Step 2: Commit**

```bash
git add src/zero_agent/history.py
git commit -m "feat: integrate memory extraction into history compression"
```

---

## P2: Skills Enhancement

### Task 8: Add Trigger Field Support

**Files:**
- Modify: `src/zero_agent/skills/loader.py`

- [ ] **Step 1: Parse trigger field from frontmatter**

- [ ] **Step 2: Commit**

---

### Task 9: Implement Skill Matching

**Files:**
- Create: `src/zero_agent/skills/matcher.py`

- [ ] **Step 1: Implement rule-based filtering**

- [ ] **Step 2: Implement LLM precise matching**

- [ ] **Step 3: Commit**

---

## P3: Configuration Simplification

### Task 10: Two-Tier Config

**Files:**
- Modify: `src/zero_agent/config.py`

- [ ] **Step 1: Update config loading for two tiers only**

- [ ] **Step 2: Add auto-create project config**

- [ ] **Step 3: Commit**

---

## P4: CLI Enhancement

### Task 11: Add --trust and --memory Parameters

**Files:**
- Modify: `src/zero_agent/cli.py`

- [ ] **Step 1: Add --trust parameter**

- [ ] **Step 2: Add --memory parameter**

- [ ] **Step 3: Commit**

---

## Final Task: Integration Testing

### Task 12: Verify All Features

- [ ] **Step 1: Test path trust in REPL mode**
- [ ] **Step 2: Test path trust in TUI mode**
- [ ] **Step 3: Test memory persistence**
- [ ] **Step 4: Test skill auto-trigger**
- [ ] **Step 5: Test config auto-create**
- [ ] **Step 6: Test CLI parameters**
