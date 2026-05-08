# Zero Agent 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个最小化的 CLI Agent，支持 MCP、Skills、安全控制和 YOLO 模式，对小模型友好。

**Architecture:** 分层架构 - CLI 层 → Agent 核心 → (LLM/Skills/Security) → 工具层 (Builtin + MCP)

**Tech Stack:** Python 3.11+, Ollama, MCP SDK, PyYAML, prompt-toolkit (REPL)

---

## 文件结构

```
src/zero_agent/
├── __init__.py           # 包入口，版本信息
├── cli.py                # CLI 入口，参数解析，REPL/单次模式
├── agent.py              # Agent 核心，对话循环，工具调度
├── llm.py                # Ollama API 适配器
├── history.py            # 对话历史管理 + 摘要压缩
├── config.py             # 配置加载和管理
├── mcp/
│   ├── __init__.py       # MCP 模块入口
│   ├── client.py         # MCP 客户端连接管理
│   └── types.py          # MCP 类型定义
├── skills/
│   ├── __init__.py       # Skills 模块入口
│   └── loader.py         # Skills 文件加载器
├── security/
│   ├── __init__.py       # Security 模块入口，SecurityManager
│   ├── permission.py     # 权限管理
│   └── risk_detector.py  # 风险检测
└── builtin/
    ├── __init__.py       # Builtin 模块入口，工具注册
    └── shell.py          # Shell 工具实现

tests/
├── test_config.py
├── test_llm.py
├── test_history.py
├── test_security.py
├── test_skills.py
├── test_builtin.py
└── test_agent.py
```

---

### Task 1: 项目基础设置

**Files:**
- Modify: `pyproject.toml`
- Create: `src/zero_agent/__init__.py`
- Create: `config.yaml`

- [ ] **Step 1: 更新 pyproject.toml 添加依赖**

```toml
[project]
name = "zero-agent"
version = "0.1.0"
description = "A minimal CLI agent with MCP, Skills, and security control"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "ollama>=0.4.0",
    "mcp>=1.0.0",
    "pyyaml>=6.0",
    "prompt-toolkit>=3.0.0",
    "click>=8.0.0",
]

[project.scripts]
zero-agent = "zero_agent.cli:main"

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 2: 创建包入口文件**

```python
# src/zero_agent/__init__.py
"""Zero Agent - A minimal CLI agent with MCP, Skills, and security control."""

__version__ = "0.1.0"
```

- [ ] **Step 3: 创建默认配置文件**

```yaml
# config.yaml
llm:
  base_url: "http://localhost:11434"
  model: "gemma3:4b"
  num_ctx: 8192
  num_predict: 2048

mcp_servers: {}

skill_paths:
  - "~/.zero-agent/skills"
  - "./.zero-agent/skills"

security:
  permissions:
    run_shell: confirm
  yolo_mode: false
  shell:
    timeout: 30
    blocked_commands:
      - "rm -rf /"
      - "mkfs"
      - "dd if="
    confirm_patterns:
      - "rm"
      - "sudo"
      - "git push"
      - "chmod"

history:
  max_tokens: 8000
  compress_threshold: 0.8
```

- [ ] **Step 4: 安装依赖**

Run: `cd /home/gem/zero-agent && uv sync`
Expected: 依赖安装成功

- [ ] **Step 5: 提交**

```bash
git add pyproject.toml src/zero_agent/__init__.py config.yaml
git commit -m "feat: project setup with dependencies and default config"
```

---

### Task 2: 配置管理模块

**Files:**
- Create: `src/zero_agent/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: 编写配置模块测试**

```python
# tests/test_config.py
import pytest
from pathlib import Path
from zero_agent.config import Config, load_config, find_config_files


def test_load_default_config():
    """测试加载默认配置"""
    config = load_config()
    assert config.llm.base_url == "http://localhost:11434"
    assert config.llm.model == "gemma3:4b"
    assert config.security.yolo_mode is False


def test_load_config_from_file(tmp_path):
    """测试从文件加载配置"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text("""
llm:
  model: "llama3"
  base_url: "http://localhost:11435"
""")
    config = load_config(str(config_file))
    assert config.llm.model == "llama3"
    assert config.llm.base_url == "http://localhost:11435"


def test_config_merge_with_defaults():
    """测试配置与默认值合并"""
    config = load_config()
    # 默认值应该存在
    assert config.history.max_tokens == 8000
    assert config.history.compress_threshold == 0.8


def test_find_config_files(tmp_path, monkeypatch):
    """测试查找配置文件"""
    # 设置项目目录
    monkeypatch.chdir(tmp_path)
    project_config = tmp_path / "config.yaml"
    project_config.write_text("llm:\n  model: test")

    files = find_config_files()
    assert len(files) >= 1
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd /home/gem/zero-agent && pytest tests/test_config.py -v`
Expected: FAIL (模块不存在)

- [ ] **Step 3: 实现配置模块**

```python
# src/zero_agent/config.py
"""Configuration management for zero-agent."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class LLMConfig:
    base_url: str = "http://localhost:11434"
    model: str = "gemma3:4b"
    num_ctx: int = 8192
    num_predict: int = 2048


@dataclass
class SecurityConfig:
    permissions: dict = field(default_factory=lambda: {"run_shell": "confirm"})
    yolo_mode: bool = False
    shell_timeout: int = 30
    blocked_commands: list = field(default_factory=lambda: ["rm -rf /", "mkfs", "dd if="])
    confirm_patterns: list = field(default_factory=lambda: ["rm", "sudo", "git push", "chmod"])


@dataclass
class HistoryConfig:
    max_tokens: int = 8000
    compress_threshold: float = 0.8


@dataclass
class Config:
    llm: LLMConfig = field(default_factory=LLMConfig)
    mcp_servers: dict = field(default_factory=dict)
    skill_paths: list = field(default_factory=lambda: ["~/.zero-agent/skills", "./.zero-agent/skills"])
    security: SecurityConfig = field(default_factory=SecurityConfig)
    history: HistoryConfig = field(default_factory=HistoryConfig)


DEFAULT_CONFIG_PATHS = [
    Path.home() / ".zero-agent" / "config.yaml",
    Path.cwd() / "config.yaml",
    Path.cwd() / ".zero-agent" / "config.yaml",
]


def find_config_files() -> list[Path]:
    """查找配置文件，按优先级返回存在的路径列表。"""
    found = []
    for path in DEFAULT_CONFIG_PATHS:
        expanded = Path(os.path.expanduser(str(path)))
        if expanded.exists():
            found.append(expanded)
    return found


def _deep_merge(base: dict, override: dict) -> dict:
    """深度合并两个字典。"""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _get_default_config() -> dict:
    """获取默认配置字典。"""
    return {
        "llm": {
            "base_url": "http://localhost:11434",
            "model": "gemma3:4b",
            "num_ctx": 8192,
            "num_predict": 2048,
        },
        "mcp_servers": {},
        "skill_paths": ["~/.zero-agent/skills", "./.zero-agent/skills"],
        "security": {
            "permissions": {"run_shell": "confirm"},
            "yolo_mode": False,
            "shell": {
                "timeout": 30,
                "blocked_commands": ["rm -rf /", "mkfs", "dd if="],
                "confirm_patterns": ["rm", "sudo", "git push", "chmod"],
            },
        },
        "history": {
            "max_tokens": 8000,
            "compress_threshold": 0.8,
        },
    }


def load_config(path: str | None = None) -> Config:
    """加载配置文件。

    优先级：指定路径 > 项目配置 > 全局配置 > 默认值
    """
    default_config = _get_default_config()
    merged_config = default_config.copy()

    if path:
        config_path = Path(os.path.expanduser(path))
        if config_path.exists():
            with open(config_path) as f:
                user_config = yaml.safe_load(f) or {}
            merged_config = _deep_merge(merged_config, user_config)
    else:
        for config_path in find_config_files():
            with open(config_path) as f:
                user_config = yaml.safe_load(f) or {}
            merged_config = _deep_merge(merged_config, user_config)

    # 构建 Config 对象
    llm_config = LLMConfig(**merged_config.get("llm", {}))

    security_data = merged_config.get("security", {})
    shell_config = security_data.get("shell", {})
    security_config = SecurityConfig(
        permissions=security_data.get("permissions", {"run_shell": "confirm"}),
        yolo_mode=security_data.get("yolo_mode", False),
        shell_timeout=shell_config.get("timeout", 30),
        blocked_commands=shell_config.get("blocked_commands", []),
        confirm_patterns=shell_config.get("confirm_patterns", []),
    )

    history_config = HistoryConfig(**merged_config.get("history", {}))

    return Config(
        llm=llm_config,
        mcp_servers=merged_config.get("mcp_servers", {}),
        skill_paths=merged_config.get("skill_paths", ["~/.zero-agent/skills"]),
        security=security_config,
        history=history_config,
    )
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd /home/gem/zero-agent && pytest tests/test_config.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add src/zero_agent/config.py tests/test_config.py
git commit -m "feat: add configuration management module"
```

---

### Task 3: LLM 适配器

**Files:**
- Create: `src/zero_agent/llm.py`
- Create: `tests/test_llm.py`

- [ ] **Step 1: 编写 LLM 适配器测试**

```python
# tests/test_llm.py
import pytest
from unittest.mock import Mock, patch
from zero_agent.llm import OllamaAdapter
from zero_agent.config import LLMConfig


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

    simplified = adapter._simplify_tools(tools)
    assert len(simplified) == 1
    assert simplified[0]["type"] == "function"
    assert "name" in simplified[0]["function"]


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
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd /home/gem/zero-agent && pytest tests/test_llm.py -v`
Expected: FAIL (模块不存在)

- [ ] **Step 3: 实现 LLM 适配器**

```python
# src/zero_agent/llm.py
"""Ollama API adapter for zero-agent."""

from dataclasses import dataclass
from typing import Any

import ollama

from zero_agent.config import LLMConfig


@dataclass
class ChatResponse:
    """LLM 响应封装。"""
    content: str
    tool_calls: list[dict] | None = None


class OllamaAdapter:
    """Ollama API 适配器，针对小模型优化。"""

    def __init__(self, config: LLMConfig):
        self.base_url = config.base_url
        self.model = config.model
        self.num_ctx = config.num_ctx
        self.num_predict = config.num_predict
        self._client = None

    def _get_client(self):
        """懒加载 Ollama 客户端。"""
        if self._client is None:
            self._client = ollama.Client(host=self.base_url)
        return self._client

    def _simplify_tools(self, tools: list[dict]) -> list[dict]:
        """精简工具描述，适合小模型。

        只保留 name + description + 必要参数，减少 token 消耗。
        """
        simplified = []
        for tool in tools:
            simplified.append({
                "type": "function",
                "function": {
                    "name": tool.get("name", ""),
                    "description": tool.get("description", "")[:200],  # 限制描述长度
                    "parameters": {
                        "type": "object",
                        "properties": tool.get("parameters", {}),
                        "required": list(tool.get("parameters", {}).keys()),
                    },
                },
            })
        return simplified

    def estimate_tokens(self, messages: list[dict]) -> int:
        """估算消息的 token 数量。

        简单估算：平均每个字符约 0.25 tokens（英文），中文约 0.5。
        """
        total_chars = 0
        for msg in messages:
            content = msg.get("content", "")
            total_chars += len(content)
            # 添加消息格式的开销
            total_chars += 20
        return int(total_chars * 0.3)  # 保守估计

    def chat(self, messages: list[dict], tools: list[dict] | None = None) -> ChatResponse:
        """发送对话请求。

        Args:
            messages: 对话消息列表
            tools: 可用工具列表

        Returns:
            ChatResponse: 包含响应内容和工具调用
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
        """生成历史摘要，用于压缩对话历史。

        Args:
            messages: 需要摘要的消息列表

        Returns:
            str: 摘要文本
        """
        if not messages:
            return ""

        # 构建摘要请求
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
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd /home/gem/zero-agent && pytest tests/test_llm.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add src/zero_agent/llm.py tests/test_llm.py
git commit -m "feat: add Ollama adapter with small model optimizations"
```

---

### Task 4: 历史管理模块

**Files:**
- Create: `src/zero_agent/history.py`
- Create: `tests/test_history.py`

- [ ] **Step 1: 编写历史管理测试**

```python
# tests/test_history.py
import pytest
from zero_agent.history import HistoryManager
from zero_agent.config import HistoryConfig


def test_history_add():
    """测试添加消息"""
    config = HistoryConfig()
    history = HistoryManager(config)

    history.add("user", "Hello")
    history.add("assistant", "Hi there")

    assert len(history.messages) == 2
    assert history.messages[0]["role"] == "user"


def test_history_get_messages():
    """测试获取消息列表"""
    config = HistoryConfig()
    history = HistoryManager(config)

    history.add("user", "Hello")
    history.add("assistant", "Hi")

    messages = history.get_messages()
    assert len(messages) == 2


def test_history_clear():
    """测试清空历史"""
    config = HistoryConfig()
    history = HistoryManager(config)

    history.add("user", "Hello")
    history.clear()

    assert len(history.messages) == 0


def test_history_should_compress():
    """测试压缩判断"""
    config = HistoryConfig(max_tokens=100, compress_threshold=0.8)
    history = HistoryManager(config)

    # 添加足够多的消息触发压缩阈值
    for i in range(10):
        history.add("user", f"Message {i} " * 50)  # 每条约 300 字符

    # 应该需要压缩
    assert history.should_compress()


def test_history_compress():
    """测试历史压缩"""
    config = HistoryConfig(max_tokens=1000)
    history = HistoryManager(config)

    # 添加多条消息
    for i in range(5):
        history.add("user", f"User message {i}")
        history.add("assistant", f"Assistant response {i}")

    original_count = len(history.messages)

    # 模拟压缩（用 mock LLM）
    from unittest.mock import Mock
    mock_llm = Mock()
    mock_llm.generate_summary.return_value = "Summary of previous conversation"

    history.compress(mock_llm)

    # 压缩后消息应该减少
    assert len(history.messages) < original_count
    assert history.messages[0]["role"] == "system"  # 摘要作为 system 消息
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd /home/gem/zero-agent && pytest tests/test_history.py -v`
Expected: FAIL (模块不存在)

- [ ] **Step 3: 实现历史管理模块**

```python
# src/zero_agent/history.py
"""Conversation history management with compression support."""

from dataclasses import dataclass, field
from typing import Any

from zero_agent.config import HistoryConfig


@dataclass
class HistoryManager:
    """对话历史管理器，支持摘要压缩。"""

    config: HistoryConfig
    messages: list[dict] = field(default_factory=list)

    def add(self, role: str, content: str, **kwargs: Any) -> None:
        """添加消息到历史。"""
        message = {"role": role, "content": content}
        message.update(kwargs)
        self.messages.append(message)

    def get_messages(self) -> list[dict]:
        """获取所有消息。"""
        return self.messages.copy()

    def clear(self) -> None:
        """清空历史。"""
        self.messages.clear()

    def get_token_count(self) -> int:
        """估算当前历史的 token 数。"""
        total_chars = 0
        for msg in self.messages:
            content = msg.get("content", "")
            total_chars += len(content) + 20  # 消息格式开销
        return int(total_chars * 0.3)

    def should_compress(self) -> bool:
        """判断是否需要压缩。"""
        current_tokens = self.get_token_count()
        threshold = self.config.max_tokens * self.config.compress_threshold
        return current_tokens >= threshold

    def compress(self, llm: Any) -> None:
        """生成摘要替换旧消息。

        保留最近的消息，将旧消息压缩为摘要。
        """
        if len(self.messages) < 4:
            return  # 消息太少，不压缩

        # 保留最近 2 轮对话（4 条消息）
        old_messages = self.messages[:-4]
        recent_messages = self.messages[-4:]

        if not old_messages:
            return

        # 生成摘要
        summary = llm.generate_summary(old_messages)

        # 用摘要替换旧消息
        self.messages = [
            {"role": "system", "content": f"[Previous conversation summary]\n{summary}"},
            *recent_messages,
        ]
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd /home/gem/zero-agent && pytest tests/test_history.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add src/zero_agent/history.py tests/test_history.py
git commit -m "feat: add history management with compression support"
```

---

### Task 5: 安全控制模块

**Files:**
- Create: `src/zero_agent/security/__init__.py`
- Create: `src/zero_agent/security/permission.py`
- Create: `src/zero_agent/security/risk_detector.py`
- Create: `tests/test_security.py`

- [ ] **Step 1: 编写安全模块测试**

```python
# tests/test_security.py
import pytest
from zero_agent.security import SecurityManager, Decision
from zero_agent.security.permission import PermissionManager
from zero_agent.security.risk_detector import RiskDetector
from zero_agent.config import SecurityConfig


def test_permission_allow():
    """测试权限允许"""
    config = SecurityConfig(permissions={"run_shell": "allow"})
    pm = PermissionManager(config)

    decision = pm.check("run_shell", {"command": "ls"})
    assert decision == Decision.ALLOW


def test_permission_deny():
    """测试权限拒绝"""
    config = SecurityConfig(permissions={"run_shell": "deny"})
    pm = PermissionManager(config)

    decision = pm.check("run_shell", {"command": "ls"})
    assert decision == Decision.DENY


def test_permission_confirm():
    """测试需要确认"""
    config = SecurityConfig(permissions={"run_shell": "confirm"})
    pm = PermissionManager(config)

    decision = pm.check("run_shell", {"command": "ls"})
    assert decision == Decision.CONFIRM


def test_risk_detector_blocked():
    """测试禁止命令检测"""
    config = SecurityConfig(
        blocked_commands=["rm -rf /", "mkfs"]
    )
    rd = RiskDetector(config)

    assert rd.is_blocked("rm -rf /") is True
    assert rd.is_blocked("mkfs /dev/sda1") is True
    assert rd.is_blocked("ls -la") is False


def test_risk_detector_needs_confirm():
    """测试高风险命令检测"""
    config = SecurityConfig(
        confirm_patterns=["rm", "sudo", "git push"]
    )
    rd = RiskDetector(config)

    assert rd.needs_confirm("rm file.txt") is True
    assert rd.needs_confirm("sudo apt install") is True
    assert rd.needs_confirm("git push origin main") is True
    assert rd.needs_confirm("ls -la") is False


def test_security_manager_normal_mode():
    """测试正常模式"""
    config = SecurityConfig(
        permissions={"run_shell": "allow"},
        blocked_commands=["rm -rf /"],
        confirm_patterns=["rm"],
    )
    sm = SecurityManager(config, yolo=False)

    # 禁止命令应该被拒绝
    assert sm.check("run_shell", {"command": "rm -rf /"}) == Decision.DENY

    # 高风险命令需要确认（即使权限是 allow）
    assert sm.check("run_shell", {"command": "rm file.txt"}) == Decision.CONFIRM

    # 普通命令允许
    assert sm.check("run_shell", {"command": "ls -la"}) == Decision.ALLOW


def test_security_manager_yolo_mode():
    """测试 YOLO 模式"""
    config = SecurityConfig(
        permissions={"run_shell": "confirm"},
        blocked_commands=["rm -rf /"],
        confirm_patterns=["rm"],
    )
    sm = SecurityManager(config, yolo=True)

    # 禁止命令仍然被拒绝
    assert sm.check("run_shell", {"command": "rm -rf /"}) == Decision.DENY

    # 高风险命令需要确认
    assert sm.check("run_shell", {"command": "rm file.txt"}) == Decision.CONFIRM

    # 普通命令自动允许（跳过权限检查）
    assert sm.check("run_shell", {"command": "ls -la"}) == Decision.ALLOW
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd /home/gem/zero-agent && pytest tests/test_security.py -v`
Expected: FAIL (模块不存在)

- [ ] **Step 3: 实现安全模块**

```python
# src/zero_agent/security/__init__.py
"""Security module for zero-agent."""

from enum import Enum

from zero_agent.security.permission import PermissionManager
from zero_agent.security.risk_detector import RiskDetector
from zero_agent.config import SecurityConfig


class Decision(Enum):
    """安全决策结果。"""
    ALLOW = "allow"
    DENY = "deny"
    CONFIRM = "confirm"


class SecurityManager:
    """安全管理器，整合权限控制和风险检测。"""

    def __init__(self, config: SecurityConfig, yolo: bool = False):
        self.yolo = yolo
        self.permissions = PermissionManager(config)
        self.risk_detector = RiskDetector(config)

    def check(self, tool_name: str, args: dict) -> Decision:
        """检查工具调用是否允许。

        Args:
            tool_name: 工具名称
            args: 工具参数

        Returns:
            Decision: ALLOW / DENY / CONFIRM
        """
        command = args.get("command", "")

        # 禁止命令永远拒绝
        if self.risk_detector.is_blocked(command):
            return Decision.DENY

        if self.yolo:
            # YOLO 模式：只对高风险确认
            if self.risk_detector.needs_confirm(command):
                return Decision.CONFIRM
            return Decision.ALLOW

        # 正常模式：检查权限 + 风险
        if self.risk_detector.needs_confirm(command):
            return Decision.CONFIRM

        return self.permissions.check(tool_name, args)


__all__ = ["Decision", "SecurityManager", "PermissionManager", "RiskDetector"]
```

```python
# src/zero_agent/security/permission.py
"""Permission management for tool execution."""

from zero_agent.config import SecurityConfig
from zero_agent.security import Decision


class PermissionManager:
    """权限管理器。"""

    def __init__(self, config: SecurityConfig):
        self.permissions = config.permissions

    def check(self, tool_name: str, args: dict) -> Decision:
        """检查工具调用权限。

        Args:
            tool_name: 工具名称
            args: 工具参数

        Returns:
            Decision: 权限决策结果
        """
        perm = self.permissions.get(tool_name, "confirm")

        if perm == "allow":
            return Decision.ALLOW
        elif perm == "deny":
            return Decision.DENY
        else:
            return Decision.CONFIRM
```

```python
# src/zero_agent/security/risk_detector.py
"""Risk detection for dangerous operations."""

from zero_agent.config import SecurityConfig


class RiskDetector:
    """风险检测器，识别危险命令。"""

    def __init__(self, config: SecurityConfig):
        self.blocked_commands = config.blocked_commands
        self.confirm_patterns = config.confirm_patterns

    def is_blocked(self, command: str) -> bool:
        """检查命令是否被禁止。

        Args:
            command: 要检查的命令

        Returns:
            bool: 是否被禁止
        """
        for blocked in self.blocked_commands:
            if blocked in command:
                return True
        return False

    def needs_confirm(self, command: str) -> bool:
        """检查命令是否需要确认。

        Args:
            command: 要检查的命令

        Returns:
            bool: 是否需要确认
        """
        for pattern in self.confirm_patterns:
            if pattern in command:
                return True
        return False
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd /home/gem/zero-agent && pytest tests/test_security.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add src/zero_agent/security/ tests/test_security.py
git commit -m "feat: add security module with permission and risk detection"
```

---

### Task 6: Skills 加载器

**Files:**
- Create: `src/zero_agent/skills/__init__.py`
- Create: `src/zero_agent/skills/loader.py`
- Create: `tests/test_skills.py`

- [ ] **Step 1: 编写 Skills 加载器测试**

```python
# tests/test_skills.py
import pytest
from pathlib import Path
from zero_agent.skills.loader import SkillLoader


def test_skill_loader_load_file(tmp_path):
    """测试加载单个 skill 文件"""
    skill_dir = tmp_path / "skills"
    skill_dir.mkdir()

    skill_file = skill_dir / "test-skill.md"
    skill_file.write_text("""---
name: test-skill
description: A test skill
trigger: when user asks for test
---

You are a test assistant.
Focus on testing.
""")

    loader = SkillLoader([str(skill_dir)])
    loader.load_all()

    assert "test-skill" in loader.skills
    assert "test assistant" in loader.skills["test-skill"]["content"]


def test_skill_loader_get_skill(tmp_path):
    """测试获取 skill 内容"""
    skill_dir = tmp_path / "skills"
    skill_dir.mkdir()

    skill_file = skill_dir / "code-review.md"
    skill_file.write_text("""---
name: code-review
description: Review code
---

You are a code reviewer.
""")

    loader = SkillLoader([str(skill_dir)])
    loader.load_all()

    content = loader.get_skill("code-review")
    assert "code reviewer" in content


def test_skill_loader_multiple_paths(tmp_path):
    """测试多路径加载（项目覆盖全局）"""
    global_dir = tmp_path / "global"
    global_dir.mkdir()
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    # 全局 skill
    global_skill = global_dir / "common.md"
    global_skill.write_text("""---
name: common
---
Global version
""")

    # 项目 skill（同名，应覆盖）
    project_skill = project_dir / "common.md"
    project_skill.write_text("""---
name: common
---
Project version
""")

    loader = SkillLoader([str(global_dir), str(project_dir)])
    loader.load_all()

    # 项目版本应该覆盖全局版本
    content = loader.get_skill("common")
    assert "Project version" in content


def test_skill_loader_get_all_prompt(tmp_path):
    """测试拼接所有 skills"""
    skill_dir = tmp_path / "skills"
    skill_dir.mkdir()

    (skill_dir / "skill1.md").write_text("""---
name: skill1
---
Content 1
""")
    (skill_dir / "skill2.md").write_text("""---
name: skill2
---
Content 2
""")

    loader = SkillLoader([str(skill_dir)])
    loader.load_all()

    prompt = loader.get_all_skills_prompt()
    assert "Content 1" in prompt
    assert "Content 2" in prompt


def test_skill_loader_missing_skill(tmp_path):
    """测试获取不存在的 skill"""
    loader = SkillLoader([str(tmp_path)])
    loader.load_all()

    content = loader.get_skill("nonexistent")
    assert content == ""
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd /home/gem/zero-agent && pytest tests/test_skills.py -v`
Expected: FAIL (模块不存在)

- [ ] **Step 3: 实现 Skills 加载器**

```python
# src/zero_agent/skills/__init__.py
"""Skills module for zero-agent."""

from zero_agent.skills.loader import SkillLoader

__all__ = ["SkillLoader"]
```

```python
# src/zero_agent/skills/loader.py
"""Skills loader for loading skill definitions from filesystem."""

import os
import re
from pathlib import Path
from typing import Any


class SkillLoader:
    """从文件系统加载 Skills。

    Skills 是 Markdown 文件，包含 frontmatter 和内容。
    后加载的路径优先级更高（项目覆盖全局）。
    """

    def __init__(self, skill_paths: list[str]):
        self.skill_paths = skill_paths
        self.skills: dict[str, dict[str, Any]] = {}

    def load_all(self) -> None:
        """从所有配置路径加载 skills。"""
        for path in self.skill_paths:
            expanded = Path(os.path.expanduser(path))
            if expanded.exists() and expanded.is_dir():
                self._load_from_dir(expanded)

    def _load_from_dir(self, directory: Path) -> None:
        """从目录加载所有 .md 文件。"""
        for file in directory.glob("*.md"):
            self._load_file(file)

    def _load_file(self, file: Path) -> None:
        """加载单个 skill 文件。"""
        try:
            content = file.read_text()
            parsed = self._parse_skill(content)
            if parsed:
                name = parsed.get("name", file.stem)
                self.skills[name] = parsed
        except Exception:
            pass  # 忽略解析失败的文件

    def _parse_skill(self, content: str) -> dict[str, Any] | None:
        """解析 skill 文件内容。

        格式:
        ---
        name: skill-name
        description: ...
        trigger: ...
        ---
        Skill content...
        """
        # 提取 frontmatter
        match = re.match(r"^---\n(.*?)\n---\n(.*)$", content, re.DOTALL)
        if not match:
            return None

        frontmatter = match.group(1)
        body = match.group(2).strip()

        # 解析 YAML frontmatter
        metadata = {}
        for line in frontmatter.split("\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                metadata[key.strip()] = value.strip()

        return {
            "name": metadata.get("name", ""),
            "description": metadata.get("description", ""),
            "trigger": metadata.get("trigger", ""),
            "content": body,
        }

    def get_skill(self, name: str) -> str:
        """获取指定 skill 的内容。"""
        skill = self.skills.get(name)
        return skill["content"] if skill else ""

    def get_all_skills_prompt(self) -> str:
        """拼接所有 skills 为一段 prompt。"""
        if not self.skills:
            return ""

        parts = []
        for name, skill in self.skills.items():
            parts.append(f"## Skill: {name}\n\n{skill['content']}\n")

        return "\n".join(parts)

    def get_skill_names(self) -> list[str]:
        """获取所有已加载的 skill 名称。"""
        return list(self.skills.keys())
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd /home/gem/zero-agent && pytest tests/test_skills.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add src/zero_agent/skills/ tests/test_skills.py
git commit -m "feat: add skills loader with multi-path support"
```

---

### Task 7: 内置工具 (Shell)

**Files:**
- Create: `src/zero_agent/builtin/__init__.py`
- Create: `src/zero_agent/builtin/shell.py`
- Create: `tests/test_builtin.py`

- [ ] **Step 1: 编写内置工具测试**

```python
# tests/test_builtin.py
import pytest
from zero_agent.builtin.shell import execute, get_tool_definition


def test_get_tool_definition():
    """测试获取工具定义"""
    tool_def = get_tool_definition()

    assert tool_def["name"] == "run_shell"
    assert "description" in tool_def
    assert "parameters" in tool_def


def test_shell_execute_simple():
    """测试执行简单命令"""
    result = execute("echo 'hello world'")

    assert result["success"] is True
    assert "hello world" in result["stdout"]


def test_shell_execute_with_timeout():
    """测试带超时执行"""
    result = execute("echo 'test'", timeout=5)

    assert result["success"] is True


def test_shell_execute_failed():
    """测试执行失败命令"""
    result = execute("ls /nonexistent_directory_12345")

    assert result["success"] is False
    assert result["stderr"] != ""


def test_shell_execute_timeout():
    """测试超时"""
    # 使用 sleep 命令测试超时
    result = execute("sleep 10", timeout=1)

    assert result["success"] is False
    assert "timeout" in result["error"].lower()
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd /home/gem/zero-agent && pytest tests/test_builtin.py -v`
Expected: FAIL (模块不存在)

- [ ] **Step 3: 实现内置工具**

```python
# src/zero_agent/builtin/__init__.py
"""Builtin tools for zero-agent."""

from zero_agent.builtin.shell import execute, get_tool_definition

__all__ = ["execute", "get_tool_definition"]
```

```python
# src/zero_agent/builtin/shell.py
"""Shell execution tool."""

import subprocess
from typing import Any


def get_tool_definition() -> dict[str, Any]:
    """获取工具定义（供 LLM 使用）。

    Returns:
        dict: 工具定义，包含 name, description, parameters
    """
    return {
        "name": "run_shell",
        "description": "Execute shell command. Use for file operations, network requests, and any system tasks.",
        "parameters": {
            "command": {
                "type": "string",
                "description": "Shell command to execute",
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds (default 30)",
            },
        },
    }


def execute(command: str, timeout: int = 30) -> dict[str, Any]:
    """执行 shell 命令。

    Args:
        command: 要执行的命令
        timeout: 超时时间（秒）

    Returns:
        dict: 包含 success, stdout, stderr, error 的结果
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
            "error": None if result.returncode == 0 else result.stderr,
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "stdout": "",
            "stderr": "",
            "returncode": -1,
            "error": f"Command timed out after {timeout} seconds",
        }

    except Exception as e:
        return {
            "success": False,
            "stdout": "",
            "stderr": "",
            "returncode": -1,
            "error": str(e),
        }
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd /home/gem/zero-agent && pytest tests/test_builtin.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add src/zero_agent/builtin/ tests/test_builtin.py
git commit -m "feat: add shell builtin tool"
```

---

### Task 8: MCP 客户端

**Files:**
- Create: `src/zero_agent/mcp/__init__.py`
- Create: `src/zero_agent/mcp/types.py`
- Create: `src/zero_agent/mcp/client.py`
- Create: `tests/test_mcp.py`

- [ ] **Step 1: 编写 MCP 客户端测试**

```python
# tests/test_mcp.py
import pytest
from zero_agent.mcp.types import Tool, ToolCall, ToolResult
from zero_agent.mcp.client import MCPClient


def test_mcp_types_tool():
    """测试 Tool 类型"""
    tool = Tool(
        name="test_tool",
        description="A test tool",
        input_schema={"type": "object"},
    )

    assert tool.name == "test_tool"
    assert tool.description == "A test tool"


def test_mcp_types_tool_call():
    """测试 ToolCall 类型"""
    call = ToolCall(
        name="test_tool",
        arguments={"arg1": "value1"},
    )

    assert call.name == "test_tool"
    assert call.arguments["arg1"] == "value1"


def test_mcp_types_tool_result():
    """测试 ToolResult 类型"""
    result = ToolResult(
        content="Result content",
        is_error=False,
    )

    assert result.content == "Result content"
    assert result.is_error is False


def test_mcp_client_init():
    """测试 MCP 客户端初始化"""
    client = MCPClient({})

    assert client.servers == {}
    assert client.tools == []


def test_mcp_client_get_tool_definitions():
    """测试获取工具定义"""
    client = MCPClient({})

    # 添加模拟工具
    from zero_agent.mcp.types import Tool
    client.tools = [
        Tool(name="tool1", description="Tool 1", input_schema={}),
        Tool(name="tool2", description="Tool 2", input_schema={}),
    ]

    definitions = client.get_tool_definitions()

    assert len(definitions) == 2
    assert definitions[0]["name"] == "tool1"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd /home/gem/zero-agent && pytest tests/test_mcp.py -v`
Expected: FAIL (模块不存在)

- [ ] **Step 3: 实现 MCP 客户端**

```python
# src/zero_agent/mcp/__init__.py
"""MCP module for zero-agent."""

from zero_agent.mcp.types import Tool, ToolCall, ToolResult
from zero_agent.mcp.client import MCPClient

__all__ = ["Tool", "ToolCall", "ToolResult", "MCPClient"]
```

```python
# src/zero_agent/mcp/types.py
"""MCP type definitions."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Tool:
    """MCP 工具定义。"""
    name: str
    description: str
    input_schema: dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolCall:
    """工具调用请求。"""
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolResult:
    """工具执行结果。"""
    content: str
    is_error: bool = False
```

```python
# src/zero_agent/mcp/client.py
"""MCP client for connecting to external MCP servers."""

import asyncio
import shutil
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from zero_agent.mcp.types import Tool, ToolCall, ToolResult


class MCPClient:
    """MCP 客户端，管理多个 MCP server 连接。"""

    def __init__(self, servers_config: dict[str, Any]):
        self.servers_config = servers_config
        self.servers: dict[str, ClientSession] = {}
        self.tools: list[Tool] = []

    async def connect_all(self) -> None:
        """连接所有配置的 MCP server。"""
        for name, config in self.servers_config.items():
            try:
                await self._connect_server(name, config)
            except Exception as e:
                print(f"Failed to connect to MCP server {name}: {e}")

    async def _connect_server(self, name: str, config: dict) -> None:
        """连接单个 MCP server。"""
        command = config.get("command")
        args = config.get("args", [])

        # 检查命令是否存在
        if not shutil.which(command):
            raise ValueError(f"Command not found: {command}")

        server_params = StdioServerParameters(
            command=command,
            args=args,
        )

        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                self.servers[name] = session

                # 获取工具列表
                tools_result = await session.list_tools()
                for tool in tools_result.tools:
                    self.tools.append(Tool(
                        name=tool.name,
                        description=tool.description or "",
                        input_schema=tool.inputSchema or {},
                    ))

    async def call_tool(self, call: ToolCall) -> ToolResult:
        """调用工具。

        Args:
            call: 工具调用请求

        Returns:
            ToolResult: 执行结果
        """
        # 找到工具所在的 server
        for name, session in self.servers.items():
            try:
                result = await session.call_tool(call.name, call.arguments)
                return ToolResult(
                    content=str(result.content),
                    is_error=result.isError if hasattr(result, "isError") else False,
                )
            except Exception:
                continue

        return ToolResult(
            content=f"Tool {call.name} not found",
            is_error=True,
        )

    def get_tool_definitions(self) -> list[dict[str, Any]]:
        """获取所有工具定义（供 LLM 使用）。"""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.input_schema.get("properties", {}),
            }
            for tool in self.tools
        ]

    def has_tools(self) -> bool:
        """检查是否有可用工具。"""
        return len(self.tools) > 0
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd /home/gem/zero-agent && pytest tests/test_mcp.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add src/zero_agent/mcp/ tests/test_mcp.py
git commit -m "feat: add MCP client for external tool servers"
```

---

### Task 9: Agent 核心

**Files:**
- Create: `src/zero_agent/agent.py`
- Create: `tests/test_agent.py`

- [ ] **Step 1: 编写 Agent 测试**

```python
# tests/test_agent.py
import pytest
from unittest.mock import Mock, patch
from zero_agent.agent import Agent
from zero_agent.config import Config, LLMConfig, SecurityConfig, HistoryConfig


def test_agent_init():
    """测试 Agent 初始化"""
    config = Config()
    agent = Agent(config)

    assert agent.config == config
    assert agent.history is not None
    assert agent.security is not None


def test_agent_build_messages():
    """测试构建消息"""
    config = Config()
    agent = Agent(config)

    messages = agent._build_messages("Hello")

    # 应包含用户消息
    assert len(messages) >= 1
    assert messages[-1]["role"] == "user"
    assert messages[-1]["content"] == "Hello"


def test_agent_build_messages_with_history():
    """测试构建消息包含历史"""
    config = Config()
    agent = Agent(config)

    # 添加历史
    agent.history.add("user", "Previous message")
    agent.history.add("assistant", "Previous response")

    messages = agent._build_messages("New message")

    # 应包含历史消息
    assert len(messages) >= 3


def test_agent_build_messages_with_skills():
    """测试构建消息包含 skills"""
    config = Config()
    agent = Agent(config)

    # 模拟 skills
    agent.skills.skills = {"test": {"content": "Test skill content"}}

    messages = agent._build_messages("Hello")

    # 应包含 skills prompt
    assert any("Test skill content" in m.get("content", "") for m in messages)


def test_agent_get_all_tools():
    """测试获取所有工具"""
    config = Config()
    agent = Agent(config)

    tools = agent._get_all_tools()

    # 应包含内置工具
    assert len(tools) >= 1
    assert any(t["name"] == "run_shell" for t in tools)
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd /home/gem/zero-agent && pytest tests/test_agent.py -v`
Expected: FAIL (模块不存在)

- [ ] **Step 3: 实现 Agent 核心**

```python
# src/zero_agent/agent.py
"""Agent core for zero-agent."""

from typing import Any

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory

from zero_agent.config import Config
from zero_agent.history import HistoryManager
from zero_agent.llm import OllamaAdapter
from zero_agent.mcp.client import MCPClient
from zero_agent.skills.loader import SkillLoader
from zero_agent.security import SecurityManager, Decision
from zero_agent.builtin.shell import execute as shell_execute, get_tool_definition


class Agent:
    """Zero Agent 核心。"""

    def __init__(self, config: Config, yolo: bool = False):
        self.config = config
        self.llm = OllamaAdapter(config.llm)
        self.history = HistoryManager(config.history)
        self.skills = SkillLoader(config.skill_paths)
        self.security = SecurityManager(config.security, yolo=yolo)
        self.mcp_client = MCPClient(config.mcp_servers)

        # 加载 skills
        self.skills.load_all()

    def _build_messages(self, user_input: str) -> list[dict]:
        """构建发送给 LLM 的消息。

        包含: system prompt + skills + 历史 + 用户输入
        """
        messages = []

        # System prompt
        system_prompt = "You are a helpful AI assistant with shell execution capabilities."
        messages.append({"role": "system", "content": system_prompt})

        # Skills prompt
        skills_prompt = self.skills.get_all_skills_prompt()
        if skills_prompt:
            messages.append({"role": "system", "content": f"Available skills:\n\n{skills_prompt}"})

        # 历史消息
        messages.extend(self.history.get_messages())

        # 用户输入
        messages.append({"role": "user", "content": user_input})

        return messages

    def _get_all_tools(self) -> list[dict]:
        """获取所有可用工具（内置 + MCP）。"""
        tools = []

        # 内置工具
        tools.append(get_tool_definition())

        # MCP 工具
        if self.mcp_client.has_tools():
            tools.extend(self.mcp_client.get_tool_definitions())

        return tools

    def _handle_tool_call(self, tool_name: str, args: dict) -> str:
        """处理工具调用。

        Args:
            tool_name: 工具名称
            args: 工具参数

        Returns:
            str: 工具执行结果
        """
        # 安全检查
        decision = self.security.check(tool_name, args)

        if decision == Decision.DENY:
            return f"Error: Tool call '{tool_name}' is denied by security policy."

        if decision == Decision.CONFIRM:
            # 需要用户确认
            confirm = input(f"Allow tool call: {tool_name}({args})? [y/N]: ")
            if confirm.lower() != "y":
                return "Error: Tool call cancelled by user."

        # 执行工具
        if tool_name == "run_shell":
            result = shell_execute(
                command=args.get("command", ""),
                timeout=args.get("timeout", 30),
            )
            if result["success"]:
                return result["stdout"] or "(no output)"
            else:
                return f"Error: {result['error']}"
        else:
            # MCP 工具
            # TODO: 异步调用
            return f"Error: Unknown tool '{tool_name}'"

    def _process_response(self, response) -> str:
        """处理 LLM 响应。

        Args:
            response: LLM 响应

        Returns:
            str: 最终输出
        """
        # 如果有工具调用
        if response.tool_calls:
            results = []
            for call in response.tool_calls:
                tool_name = call.get("function", {}).get("name", "")
                args = call.get("function", {}).get("arguments", {})

                result = self._handle_tool_call(tool_name, args)
                results.append(f"[{tool_name}]: {result}")

            return "\n".join(results)

        return response.content

    def run_once(self, prompt: str) -> str:
        """单次执行模式。

        Args:
            prompt: 用户输入

        Returns:
            str: 执行结果
        """
        messages = self._build_messages(prompt)
        tools = self._get_all_tools()

        response = self.llm.chat(messages, tools)
        result = self._process_response(response)

        # 更新历史
        self.history.add("user", prompt)
        self.history.add("assistant", result)

        return result

    def start_repl(self) -> None:
        """启动 REPL 交互模式。"""
        print("Zero Agent REPL. Type /exit to quit, /clear to clear history.")

        session = PromptSession(history=FileHistory(".zero_agent_history"))

        while True:
            try:
                user_input = session.prompt(">>> ").strip()

                if not user_input:
                    continue

                # 处理命令
                if user_input == "/exit":
                    print("Goodbye!")
                    break

                if user_input == "/clear":
                    self.history.clear()
                    print("History cleared.")
                    continue

                if user_input == "/help":
                    print("Commands: /exit, /clear, /help, /yolo, /safe")
                    continue

                if user_input == "/yolo":
                    self.security.yolo = True
                    print("YOLO mode enabled.")
                    continue

                if user_input == "/safe":
                    self.security.yolo = False
                    print("Safe mode enabled.")
                    continue

                # 执行对话
                messages = self._build_messages(user_input)
                tools = self._get_all_tools()

                response = self.llm.chat(messages, tools)
                result = self._process_response(response)

                # 更新历史
                self.history.add("user", user_input)
                self.history.add("assistant", result)

                # 检查是否需要压缩
                if self.history.should_compress():
                    self.history.compress(self.llm)

                print(result)

            except KeyboardInterrupt:
                print("\nUse /exit to quit.")
                continue

            except EOFError:
                print("\nGoodbye!")
                break
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd /home/gem/zero-agent && pytest tests/test_agent.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add src/zero_agent/agent.py tests/test_agent.py
git commit -m "feat: add agent core with REPL and tool dispatch"
```

---

### Task 10: CLI 入口

**Files:**
- Create: `src/zero_agent/cli.py`

- [ ] **Step 1: 实现 CLI 入口**

```python
# src/zero_agent/cli.py
"""CLI entry point for zero-agent."""

import click

from zero_agent import __version__
from zero_agent.agent import Agent
from zero_agent.config import load_config


@click.command()
@click.version_option(version=__version__)
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=False),
    help="Path to config file",
)
@click.option(
    "--once",
    "-o",
    "prompt",
    help="Run once with the given prompt and exit",
)
@click.option(
    "--yolo",
    "-y",
    is_flag=True,
    help="Enable YOLO mode (only confirm high-risk operations)",
)
def main(config: str | None, prompt: str | None, yolo: bool) -> None:
    """Zero Agent - A minimal CLI agent with MCP, Skills, and security control."""
    # 加载配置
    cfg = load_config(config)

    # 创建 Agent
    agent = Agent(cfg, yolo=yolo)

    if prompt:
        # 单次执行模式
        result = agent.run_once(prompt)
        print(result)
    else:
        # REPL 模式
        agent.start_repl()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 测试 CLI 帮助信息**

Run: `cd /home/gem/zero-agent && uv run zero-agent --help`
Expected: 显示帮助信息

- [ ] **Step 3: 测试单次执行**

Run: `cd /home/gem/zero-agent && uv run zero-agent --once "What is 2+2?"`
Expected: 返回 LLM 响应（需要 Ollama 运行）

- [ ] **Step 4: 提交**

```bash
git add src/zero_agent/cli.py
git commit -m "feat: add CLI entry point with REPL and once mode"
```

---

### Task 11: 最终集成测试

**Files:**
- Create: `tests/test_integration.py`

- [ ] **Step 1: 编写集成测试**

```python
# tests/test_integration.py
"""Integration tests for zero-agent."""

import pytest
from zero_agent.config import load_config
from zero_agent.agent import Agent


def test_agent_full_flow():
    """测试完整流程（不调用 LLM）"""
    config = load_config()
    agent = Agent(config)

    # 测试消息构建
    messages = agent._build_messages("Hello")
    assert len(messages) >= 2

    # 测试工具获取
    tools = agent._get_all_tools()
    assert len(tools) >= 1

    # 测试安全检查
    from zero_agent.security import Decision
    decision = agent.security.check("run_shell", {"command": "ls"})
    assert decision in [Decision.ALLOW, Decision.CONFIRM, Decision.DENY]


def test_agent_with_yolo_mode():
    """测试 YOLO 模式"""
    config = load_config()
    agent = Agent(config, yolo=True)

    assert agent.security.yolo is True

    # 普通命令应该允许
    from zero_agent.security import Decision
    decision = agent.security.check("run_shell", {"command": "ls"})
    assert decision == Decision.ALLOW


def test_agent_history_compression():
    """测试历史压缩"""
    config = load_config()
    agent = Agent(config)

    # 添加足够多的消息
    for i in range(10):
        agent.history.add("user", f"Message {i} " * 100)

    # 检查是否需要压缩
    assert agent.history.should_compress() or len(agent.history.messages) < 10
```

- [ ] **Step 2: 运行所有测试**

Run: `cd /home/gem/zero-agent && pytest -v`
Expected: 所有测试通过

- [ ] **Step 3: 提交**

```bash
git add tests/test_integration.py
git commit -m "test: add integration tests"
```

---

### Task 12: 文档和清理

**Files:**
- Modify: `README.md`

- [ ] **Step 1: 更新 README**

```markdown
# Zero Agent

A minimal CLI agent with MCP, Skills, and security control, optimized for small models like Gemma 4.

## Features

- **CLI Modes**: REPL and single-shot execution
- **MCP Client**: Connect to external MCP servers for tools
- **Skills**: Load skill prompts from `.md` files
- **Security**: Permission control + risk detection
- **YOLO Mode**: Auto-execute safe operations, only confirm high-risk
- **Small Model Friendly**: Compressed prompts, history summarization

## Installation

```bash
uv sync
```

## Usage

### REPL Mode

```bash
uv run zero-agent
```

### Single Execution

```bash
uv run zero-agent --once "Your prompt here"
```

### YOLO Mode

```bash
uv run zero-agent --yolo
```

## Configuration

Edit `config.yaml` or `~/.zero-agent/config.yaml`:

```yaml
llm:
  model: "gemma3:4b"
  base_url: "http://localhost:11434"

security:
  yolo_mode: false
  permissions:
    run_shell: confirm
```

## Skills

Place `.md` files in `~/.zero-agent/skills/` or `./.zero-agent/skills/`:

```markdown
---
name: code-review
description: Review code
---

You are a code reviewer...
```

## REPL Commands

- `/exit` - Exit REPL
- `/clear` - Clear history
- `/yolo` - Enable YOLO mode
- `/safe` - Enable safe mode
- `/help` - Show help
```

- [ ] **Step 2: 提交**

```bash
git add README.md
git commit -m "docs: update README with usage instructions"
```

- [ ] **Step 3: 最终检查**

Run: `cd /home/gem/zero-agent && pytest -v && uv run zero-agent --help`
Expected: 测试通过，帮助信息显示正确

---

## 实现顺序总结

1. Task 1: 项目基础设置
2. Task 2: 配置管理模块
3. Task 3: LLM 适配器
4. Task 4: 历史管理模块
5. Task 5: 安全控制模块
6. Task 6: Skills 加载器
7. Task 7: 内置工具 (Shell)
8. Task 8: MCP 客户端
9. Task 9: Agent 核心
10. Task 10: CLI 入口
11. Task 11: 最终集成测试
12. Task 12: 文档和清理

每个 Task 都是独立的，可以按顺序执行。每个 Task 内部的步骤遵循 TDD 流程：写测试 → 运行失败 → 实现 → 运行通过 → 提交。