# Zero Agent - Claude Code CLI 风格 TUI 设计

## 概述

本文档基于 Claude Code CLI 的核心交互模式，为 zero-agent 项目提供详细的 TUI (Terminal User Interface) 设计参考。

## 一、核心架构设计

### 1.1 整体架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                          Zero Agent TUI                              │
├─────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                    App (Textual Application)                │    │
│  │  ┌─────────────────────────────────────────────────────┐    │    │
│  │  │                   Screen Layer                      │    │    │
│  │  │  ┌─────────────────────────────────────────────┐    │    │    │
│  │  │  │              Header Widget                   │    │    │    │
│  │  │  │  [Mode: ask] [Lang: zh] [Model: gemma3:4b]  │    │    │    │
│  │  │  └─────────────────────────────────────────────┘    │    │    │
│  │  │  ┌─────────────────────────────────────────────┐    │    │    │
│  │  │  │              Message List                    │    │    │    │
│  │  │  │  (Scrollable conversation history)          │    │    │    │
│  │  │  │                                              │    │    │    │
│  │  │  │  User: ...                                  │    │    │    │
│  │  │  │  Assistant: ...                             │    │    │    │
│  │  │  │  [Tool: run_shell] ls -la                   │    │    │    │
│  │  │  │  [Result] total 32                          │    │    │    │
│  │  │  └─────────────────────────────────────────────┘    │    │    │
│  │  │  ┌─────────────────────────────────────────────┐    │    │    │
│  │  │  │              Input Widget                   │    │    │    │
│  │  │  │  >>> Your message here...                   │    │    │    │
│  │  │  └─────────────────────────────────────────────┘    │    │    │
│  │  │  ┌─────────────────────────────────────────────┐    │    │    │
│  │  │  │              Footer Widget                  │    │    │    │
│  │  │  │  [Tab] Mode  [Ctrl+T] Lang  [/help] Help   │    │    │    │
│  │  │  └─────────────────────────────────────────────┘    │    │    │
│  │  └─────────────────────────────────────────────────────┘    │    │
│  └─────────────────────────────────────────────────────────────┘    │
├─────────────────────────────────────────────────────────────────────┤
│                       Core Components                                │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌────────────┐ │
│  │   Message    │ │   Tool       │ │ Permission   │ │   MCP      │ │
│  │   Processor  │ │   Executor   │ │   Manager    │ │   Client   │ │
│  └──────────────┘ └──────────────┘ └──────────────┘ └────────────┘ │
├─────────────────────────────────────────────────────────────────────┤
│                       Data Layer                                     │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌────────────┐ │
│  │   History    │ │   Config     │ │   Skills     │ │   State    │ │
│  │   Manager    │ │   Loader     │ │   Loader     │ │   Store    │ │
│  └──────────────┘ └──────────────┘ └──────────────┘ └────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.2 核心模块划分

```python
# src/zero_agent/tui/__init__.py
"""
TUI 模块结构:
├── __init__.py          # 导出和版本
├── app.py               # Textual Application 主类
├── screens/
│   ├── __init__.py
│   ├── main.py          # 主屏幕
│   ├── permission.py    # 权限确认弹窗
│   └── help.py          # 帮助屏幕
├── widgets/
│   ├── __init__.py
│   ├── header.py        # 状态栏
│   ├── message_list.py  # 消息列表
│   ├── message_item.py  # 单条消息
│   ├── input_box.py     # 输入框
│   ├── footer.py        # 底部快捷键栏
│   └── tool_view.py     # 工具调用展示
├── messages/
│   ├── __init__.py
│   ├── user.py          # 用户消息
│   ├── assistant.py     # 助手消息
│   ├── tool_call.py     # 工具调用消息
│   └── system.py        # 系统消息
└── styles/
    └── app.css          # Textual CSS 样式
"""
```

## 二、交互流程设计

### 2.1 消息处理流程

```
┌──────────────────────────────────────────────────────────────────┐
│                     消息处理流程                                   │
└──────────────────────────────────────────────────────────────────┘

用户输入
    │
    ▼
┌─────────────────┐
│ Input Widget    │  用户在输入框输入消息
│ (on_submit)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Message Store   │  添加用户消息到历史
│ add_message()   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ LLM Adapter     │  发送请求到 LLM
│ chat_stream()   │  使用流式输出
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────────────┐
│              响应处理循环                             │
│  ┌─────────────────────────────────────────────┐   │
│  │  流式接收响应                                 │   │
│  │  ├─ 文本内容 → 实时更新 Message Widget       │   │
│  │  └─ 工具调用 → 触发工具处理流程              │   │
│  └─────────────────────────────────────────────┘   │
│                                                     │
│  ┌─────────────────────────────────────────────┐   │
│  │  工具调用处理                                 │   │
│  │  1. 权限检查                                  │   │
│  │  2. 用户确认 (如需要)                         │   │
│  │  3. 执行工具                                  │   │
│  │  4. 返回结果                                  │   │
│  │  5. 继续对话                                  │   │
│  └─────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────┐
│ History Manager │  保存完整对话历史
│ compress()      │  检查是否需要压缩
└─────────────────┘
```

### 2.2 工具调用机制

```python
# src/zero_agent/tui/handlers/tool_handler.py
"""工具调用处理机制"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Awaitable

class ToolStatus(Enum):
    PENDING = "pending"        # 等待执行
    CONFIRMING = "confirming"  # 等待用户确认
    RUNNING = "running"        # 执行中
    SUCCESS = "success"        # 成功
    ERROR = "error"            # 失败
    DENIED = "denied"          # 被拒绝

@dataclass
class ToolCallContext:
    """工具调用上下文"""
    tool_name: str
    arguments: dict[str, Any]
    status: ToolStatus = ToolStatus.PENDING
    result: str | None = None
    error: str | None = None
    requires_confirm: bool = False

class ToolHandler:
    """工具调用处理器"""
    
    def __init__(self, app: "ZeroAgentApp"):
        self.app = app
        self.pending_calls: list[ToolCallContext] = []
    
    async def handle_tool_call(
        self, 
        tool_name: str, 
        arguments: dict[str, Any]
    ) -> str:
        """处理工具调用"""
        ctx = ToolCallContext(
            tool_name=tool_name,
            arguments=arguments
        )
        
        # 1. 权限检查
        decision = self.app.security.check(tool_name, arguments)
        
        if decision == Decision.DENY:
            ctx.status = ToolStatus.DENIED
            return self._format_denied_response(tool_name, arguments)
        
        # 2. 需要确认的情况
        if decision == Decision.CONFIRM:
            ctx.status = ToolStatus.CONFIRMING
            ctx.requires_confirm = True
            
            # 显示确认弹窗
            confirmed = await self._show_permission_dialog(ctx)
            
            if not confirmed:
                ctx.status = ToolStatus.DENIED
                return self._format_cancelled_response(tool_name)
            
            # 记住用户选择
            self.app.permission_memory.remember(tool_name, arguments)
        
        # 3. 执行工具
        ctx.status = ToolStatus.RUNNING
        self.app.update_tool_status(ctx)
        
        try:
            result = await self._execute_tool(tool_name, arguments)
            ctx.status = ToolStatus.SUCCESS
            ctx.result = result
        except Exception as e:
            ctx.status = ToolStatus.ERROR
            ctx.error = str(e)
            result = f"Error: {e}"
        
        self.app.update_tool_status(ctx)
        return result
    
    async def _show_permission_dialog(
        self, 
        ctx: ToolCallContext
    ) -> bool:
        """显示权限确认弹窗"""
        # 推送权限确认屏幕
        result = await self.app.push_screen_wait(
            PermissionScreen(ctx)
        )
        return result
    
    async def _execute_tool(
        self, 
        tool_name: str, 
        arguments: dict[str, Any]
    ) -> str:
        """执行具体工具"""
        if tool_name == "run_shell":
            return await self._execute_shell(arguments)
        else:
            # MCP 工具
            return await self.app.mcp_client.call_tool(
                ToolCall(name=tool_name, arguments=arguments)
            )
```

### 2.3 用户确认流程

```
┌──────────────────────────────────────────────────────────────────┐
│                    权限确认流程                                   │
└──────────────────────────────────────────────────────────────────┘

工具调用请求
    │
    ▼
┌─────────────────┐
│ Security Check  │
└────────┬────────┘
         │
    ┌────┴────┐
    │ Decision │
    └────┬────┘
         │
    ┌────┼────────────────────────────────────┐
    │    │                │                   │
    ▼    ▼                ▼                   ▼
 ALLOW  DENY          CONFIRM              YOLO模式
    │    │                │                   │
    │    │                ▼                   │
    │    │     ┌─────────────────┐           │
    │    │     │ Permission      │           │
    │    │     │ Dialog          │           │
    │    │     └────────┬────────┘           │
    │    │              │                     │
    │    │         ┌────┼────┐               │
    │    │         ▼         ▼               │
    │    │      [Allow]   [Deny]            │
    │    │         │         │               │
    │    │         ▼         ▼               │
    │    │    ┌────────────────────┐         │
    │    │    │ Remember choice?  │         │
    │    │    │ [For session]      │         │
    │    │    │ [Always]           │         │
    │    │    │ [Never]            │         │
    │    │    └─────────┬──────────┘         │
    │    │              │                    │
    ▼    ▼              ▼                    ▼
执行   拒绝         根据选择执行       高风险才确认
```

### 2.4 流式输出处理

```python
# src/zero_agent/tui/handlers/stream_handler.py
"""流式输出处理"""

import asyncio
from collections.abc import AsyncGenerator
from textual.message import Message

class StreamChunk(Message):
    """流式文本块消息"""
    def __init__(self, content: str, is_final: bool = False):
        self.content = content
        self.is_final = is_final
        super().__init__()

class StreamHandler:
    """流式响应处理器"""
    
    def __init__(self, app: "ZeroAgentApp"):
        self.app = app
        self.current_content = ""
        self.message_id: str | None = None
    
    async def process_stream(
        self, 
        stream: AsyncGenerator[dict, None]
    ) -> None:
        """处理流式响应"""
        self.current_content = ""
        self.message_id = self.app.create_assistant_message()
        
        try:
            async for chunk in stream:
                # 处理文本内容
                if content := chunk.get("content"):
                    self.current_content += content
                    # 发送更新消息
                    self.app.emit(StreamChunk(
                        content=self.current_content,
                        is_final=False
                    ))
                
                # 处理工具调用
                if tool_calls := chunk.get("tool_calls"):
                    for call in tool_calls:
                        await self.app.tool_handler.handle_tool_call(
                            call["function"]["name"],
                            call["function"]["arguments"]
                        )
        
        except asyncio.CancelledError:
            # 用户取消
            self.app.update_message(
                self.message_id, 
                self.current_content + "\n[Cancelled]"
            )
            return
        
        finally:
            # 标记完成
            self.app.emit(StreamChunk(
                content=self.current_content,
                is_final=True
            ))
            
            # 保存到历史
            self.app.history.add("assistant", self.current_content)
```

## 三、权限系统设计

### 3.1 权限模型

```python
# src/zero_agent/security/permission_v2.py
"""增强的权限管理系统"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import json
from typing import Any

class Permission(Enum):
    """权限级别"""
    ALLOW = "allow"           # 自动允许
    DENY = "deny"             # 永久拒绝
    CONFIRM = "confirm"       # 每次确认
    SESSION_ALLOW = "session_allow"  # 本会话允许

@dataclass
class PermissionRule:
    """权限规则"""
    tool: str                 # 工具名，支持通配符
    permission: Permission
    conditions: dict = field(default_factory=dict)
    source: str = "config"   # config, user, session
    
@dataclass
class PermissionMemory:
    """用户选择记忆"""
    session_allows: dict[str, list[str]] = field(default_factory=dict)
    always_allows: dict[str, list[str]] = field(default_factory=dict)
    never_allows: dict[str, list[str]] = field(default_factory=dict)
    
    def remember_session(self, tool: str, pattern: str) -> None:
        """记住本次会话的选择"""
        if tool not in self.session_allows:
            self.session_allows[tool] = []
        if pattern not in self.session_allows[tool]:
            self.session_allows[tool].append(pattern)
    
    def remember_always(self, tool: str, pattern: str) -> None:
        """永久记住选择"""
        if tool not in self.always_allows:
            self.always_allows[tool] = []
        if pattern not in self.always_allows[tool]:
            self.always_allows[tool].append(pattern)
    
    def is_session_allowed(self, tool: str, pattern: str) -> bool:
        """检查是否在会话白名单"""
        patterns = self.session_allows.get(tool, [])
        return any(pattern.startswith(p) for p in patterns)
    
    def is_always_allowed(self, tool: str, pattern: str) -> bool:
        """检查是否在永久白名单"""
        patterns = self.always_allows.get(tool, [])
        return any(pattern.startswith(p) for p in patterns)

class EnhancedSecurityManager:
    """增强的安全管理器"""
    
    def __init__(self, config: "SecurityConfig"):
        self.config = config
        self.rules: list[PermissionRule] = []
        self.memory = PermissionMemory()
        self.risk_detector = RiskDetector(config)
        self._load_rules()
    
    def _load_rules(self) -> None:
        """加载权限规则"""
        # 从配置文件加载
        for tool, perm in self.config.permissions.items():
            self.rules.append(PermissionRule(
                tool=tool,
                permission=Permission(perm)
            ))
    
    def check(
        self, 
        tool_name: str, 
        args: dict[str, Any],
        mode: str = "ask"
    ) -> tuple[Decision, str]:
        """检查权限
        
        Returns:
            tuple[Decision, str]: (决策, 原因)
        """
        command = args.get("command", "")
        
        # 1. 检查硬性禁止
        if self.risk_detector.is_blocked(command):
            return Decision.DENY, "Command is blocked"
        
        # 2. 检查会话记忆
        if self.memory.is_session_allowed(tool_name, command):
            return Decision.ALLOW, "Allowed in this session"
        
        # 3. 检查永久白名单
        if self.memory.is_always_allowed(tool_name, command):
            return Decision.ALLOW, "Always allowed"
        
        # 4. YOLO 模式处理
        if mode == "yolo":
            if self.risk_detector.needs_confirm(command):
                return Decision.CONFIRM, "High-risk operation"
            return Decision.ALLOW, "YOLO mode"
        
        # 5. Plan 模式处理
        if mode == "plan":
            if self._is_write_command(command):
                return Decision.DENY, "Write not allowed in plan mode"
            # 只读操作在 plan 模式下也需要确认
            return Decision.CONFIRM, "Plan mode confirmation"
        
        # 6. Ask 模式 - 按规则处理
        for rule in self.rules:
            if self._match_rule(rule, tool_name, args):
                if rule.permission == Permission.ALLOW:
                    return Decision.ALLOW, "Rule allows"
                elif rule.permission == Permission.DENY:
                    return Decision.DENY, "Rule denies"
                else:
                    break
        
        # 7. 高风险检查
        if self.risk_detector.needs_confirm(command):
            return Decision.CONFIRM, "High-risk operation"
        
        # 8. 默认需要确认
        return Decision.CONFIRM, "Default confirmation"
    
    def remember(
        self, 
        tool: str, 
        args: dict[str, Any], 
        choice: str
    ) -> None:
        """记住用户选择"""
        pattern = args.get("command", "")
        
        if choice == "session":
            self.memory.remember_session(tool, pattern)
        elif choice == "always":
            self.memory.remember_always(tool, pattern)
            self._save_to_config(tool, pattern)
        elif choice == "never":
            self.memory.remember_never(tool, pattern)
            self._save_to_config(tool, pattern, deny=True)
```

### 3.2 权限确认弹窗

```python
# src/zero_agent/tui/screens/permission.py
"""权限确认屏幕"""

from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static

class PermissionScreen(ModalScreen[bool]):
    """权限确认弹窗"""
    
    CSS_PATH = "../styles/permission.css"
    
    BINDINGS = [
        ("y", "allow", "Allow"),
        ("n", "deny", "Deny"),
        ("s", "allow_session", "Allow for session"),
        ("escape", "deny", "Cancel"),
    ]
    
    def __init__(self, ctx: "ToolCallContext"):
        self.ctx = ctx
        super().__init__()
    
    def compose(self) -> ComposeResult:
        with Container(classes="permission-dialog"):
            yield Label("Permission Required", classes="title")
            
            yield Static(
                f"Tool: [bold]{self.ctx.tool_name}[/bold]",
                classes="tool-name"
            )
            
            if command := self.ctx.arguments.get("command"):
                yield Static(
                    f"Command: [code]{command}[/code]",
                    classes="command"
                )
            
            if risk := self._get_risk_description():
                yield Static(risk, classes="risk-warning")
            
            with Horizontal(classes="buttons"):
                yield Button("Allow [y]", id="allow", variant="success")
                yield Button("Allow for session [s]", id="session", variant="primary")
                yield Button("Deny [n]", id="deny", variant="error")
    
    def _get_risk_description(self) -> str | None:
        """获取风险描述"""
        # 根据工具和参数返回风险提示
        command = self.ctx.arguments.get("command", "")
        if "rm " in command:
            return "Warning: This will delete files"
        if "sudo " in command:
            return "Warning: This requires root privileges"
        return None
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """处理按钮点击"""
        if event.button.id == "allow":
            self.dismiss(True)
        elif event.button.id == "session":
            self.app.security.remember(
                self.ctx.tool_name, 
                self.ctx.arguments, 
                "session"
            )
            self.dismiss(True)
        else:
            self.dismiss(False)
    
    def action_allow(self) -> None:
        self.dismiss(True)
    
    def action_deny(self) -> None:
        self.dismiss(False)
    
    def action_allow_session(self) -> None:
        self.app.security.remember(
            self.ctx.tool_name, 
            self.ctx.arguments, 
            "session"
        )
        self.dismiss(True)
```

## 四、斜杠命令系统

### 4.1 命令注册表

```python
# src/zero_agent/commands/registry.py
"""斜杠命令注册表"""

from dataclasses import dataclass
from typing import Callable, Any
from enum import Enum

class CommandType(Enum):
    """命令类型"""
    BUILTIN = "builtin"    # 内置命令
    SKILL = "skill"         # 技能命令
    MCP = "mcp"            # MCP 命令
    CUSTOM = "custom"      # 自定义命令

@dataclass
class Command:
    """命令定义"""
    name: str
    description: str
    handler: Callable
    type: CommandType = CommandType.BUILTIN
    aliases: list[str] = None
    usage: str = ""
    examples: list[str] = None

class CommandRegistry:
    """命令注册表"""
    
    def __init__(self):
        self._commands: dict[str, Command] = {}
        self._register_builtin_commands()
    
    def _register_builtin_commands(self) -> None:
        """注册内置命令"""
        self.register(Command(
            name="exit",
            description="Exit the application",
            handler=self._cmd_exit,
            aliases=["quit", "q"]
        ))
        
        self.register(Command(
            name="clear",
            description="Clear conversation history",
            handler=self._cmd_clear,
            aliases=["cls"]
        ))
        
        self.register(Command(
            name="help",
            description="Show available commands",
            handler=self._cmd_help,
            aliases=["?", "h"]
        ))
        
        self.register(Command(
            name="mode",
            description="Show or change current mode",
            handler=self._cmd_mode,
            usage="/mode [plan|ask|yolo]"
        ))
        
        self.register(Command(
            name="lang",
            description="Show or change current language",
            handler=self._cmd_lang,
            usage="/lang [en|zh|ja]"
        ))
        
        self.register(Command(
            name="config",
            description="Show or edit configuration",
            handler=self._cmd_config,
            usage="/config [key[=value]]"
        ))
        
        self.register(Command(
            name="skill",
            description="List or invoke skills",
            handler=self._cmd_skill,
            usage="/skill [name] [args...]"
        ))
        
        self.register(Command(
            name="mcp",
            description="Manage MCP servers",
            handler=self._cmd_mcp,
            usage="/mcp [list|connect|disconnect] [server]"
        ))
        
        self.register(Command(
            name="history",
            description="Manage conversation history",
            handler=self._cmd_history,
            usage="/history [clear|export|load]"
        ))
        
        self.register(Command(
            name="compact",
            description="Force history compression",
            handler=self._cmd_compact
        ))
    
    def register(self, command: Command) -> None:
        """注册命令"""
        self._commands[command.name] = command
        if command.aliases:
            for alias in command.aliases:
                self._commands[alias] = command
    
    def get(self, name: str) -> Command | None:
        """获取命令"""
        return self._commands.get(name)
    
    def list(self, type: CommandType | None = None) -> list[Command]:
        """列出命令"""
        commands = list(set(self._commands.values()))  # 去重
        if type:
            commands = [c for c in commands if c.type == type]
        return sorted(commands, key=lambda c: c.name)
    
    def parse(self, input: str) -> tuple[Command, list[str]] | None:
        """解析输入"""
        if not input.startswith("/"):
            return None
        
        parts = input[1:].split(maxsplit=1)
        if not parts:
            return None
        
        cmd_name = parts[0].lower()
        args_str = parts[1] if len(parts) > 1 else ""
        
        command = self.get(cmd_name)
        if not command:
            return None
        
        # 简单参数解析
        args = self._parse_args(args_str) if args_str else []
        return command, args
    
    def _parse_args(self, args_str: str) -> list[str]:
        """解析参数，支持引号"""
        args = []
        current = ""
        in_quotes = False
        quote_char = None
        
        for char in args_str:
            if char in ('"', "'") and not in_quotes:
                in_quotes = True
                quote_char = char
            elif char == quote_char and in_quotes:
                in_quotes = False
                quote_char = None
            elif char == ' ' and not in_quotes:
                if current:
                    args.append(current)
                    current = ""
            else:
                current += char
        
        if current:
            args.append(current)
        
        return args
```

### 4.2 命令处理器实现

```python
# src/zero_agent/commands/handlers.py
"""命令处理器实现"""

class CommandHandlers:
    """命令处理器集合"""
    
    def __init__(self, app: "ZeroAgentApp"):
        self.app = app
    
    def _cmd_exit(self, args: list[str]) -> str:
        """退出应用"""
        self.app.exit()
        return "Goodbye!"
    
    def _cmd_clear(self, args: list[str]) -> str:
        """清空历史"""
        self.app.history.clear()
        self.app.message_list.clear()
        return self.app.t("cleared")
    
    def _cmd_help(self, args: list[str]) -> str:
        """显示帮助"""
        lines = ["Available commands:\n"]
        
        for cmd in self.app.command_registry.list():
            line = f"  /{cmd.name}"
            if cmd.usage:
                line += f" {cmd.usage}"
            line += f" - {cmd.description}"
            if cmd.aliases:
                line += f" (aliases: {', '.join(cmd.aliases)})"
            lines.append(line)
        
        lines.append("\nKeyboard shortcuts:")
        lines.append("  Tab       - Cycle modes (plan -> ask -> yolo)")
        lines.append("  Ctrl+T    - Cycle languages")
        lines.append("  Ctrl+C    - Cancel current operation")
        lines.append("  Ctrl+L    - Clear screen")
        lines.append("  ↑/↓       - Navigate history")
        
        return "\n".join(lines)
    
    def _cmd_mode(self, args: list[str]) -> str:
        """切换或显示模式"""
        if not args:
            return f"Current mode: {self.app.mode}\nModes: plan -> ask -> yolo"
        
        new_mode = args[0].lower()
        if new_mode not in ("plan", "ask", "yolo"):
            return f"Invalid mode: {new_mode}\nValid modes: plan, ask, yolo"
        
        self.app.mode = new_mode
        self.app.security.yolo = (new_mode == "yolo")
        self.app.update_header()
        return f"Switched to {new_mode} mode"
    
    def _cmd_skill(self, args: list[str]) -> str:
        """技能管理"""
        if not args:
            # 列出所有技能
            skills = self.app.skills.get_skill_names()
            if not skills:
                return "No skills loaded"
            return "Loaded skills:\n" + "\n".join(f"  /{s}" for s in skills)
        
        skill_name = args[0]
        skill_content = self.app.skills.get_skill(skill_name)
        
        if not skill_content:
            return f"Skill not found: {skill_name}"
        
        # 执行技能
        skill_args = args[1:] if len(args) > 1 else []
        # 技能内容会作为系统提示注入
        return f"Activating skill: {skill_name}"
    
    def _cmd_config(self, args: list[str]) -> str:
        """配置管理"""
        if not args:
            # 显示当前配置
            return self._format_config()
        
        key = args[0]
        if "=" in key:
            # 设置配置
            k, v = key.split("=", 1)
            self._set_config(k.strip(), v.strip())
            return f"Set {k} = {v}"
        else:
            # 显示配置项
            return self._get_config_value(key)
```

## 五、会话管理设计

### 5.1 历史记录管理

```python
# src/zero_agent/session/history_v2.py
"""增强的历史记录管理"""

import json
import hashlib
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Any

@dataclass
class Message:
    """消息记录"""
    id: str
    role: str  # user, assistant, system, tool
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: dict = field(default_factory=dict)
    
    # 工具调用相关
    tool_calls: list[dict] = field(default_factory=list)
    tool_call_id: str | None = None
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "Message":
        return cls(**data)

@dataclass
class Session:
    """会话记录"""
    id: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    messages: list[Message] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    
    def add_message(self, message: Message) -> None:
        self.messages.append(message)
        self.updated_at = datetime.now().isoformat()
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "Session":
        data["messages"] = [Message.from_dict(m) for m in data.get("messages", [])]
        return cls(**data)

class SessionManager:
    """会话管理器"""
    
    def __init__(self, storage_path: Path | None = None):
        self.storage_path = storage_path or Path.home() / ".zero-agent" / "sessions"
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.current_session: Session | None = None
        self._load_latest_session()
    
    def _load_latest_session(self) -> None:
        """加载最近的会话"""
        sessions = sorted(
            self.storage_path.glob("*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        if sessions:
            self.current_session = self._load_session(sessions[0])
        else:
            self.current_session = Session(id=self._generate_id())
    
    def _generate_id(self) -> str:
        """生成会话 ID"""
        return hashlib.md5(
            datetime.now().isoformat().encode()
        ).hexdigest()[:8]
    
    def _load_session(self, path: Path) -> Session:
        """加载会话"""
        with open(path) as f:
            return Session.from_dict(json.load(f))
    
    def save_session(self) -> None:
        """保存当前会话"""
        if not self.current_session:
            return
        
        path = self.storage_path / f"{self.current_session.id}.json"
        with open(path, "w") as f:
            json.dump(self.current_session.to_dict(), f, indent=2)
    
    def new_session(self) -> Session:
        """创建新会话"""
        self.save_session()
        self.current_session = Session(id=self._generate_id())
        return self.current_session
    
    def list_sessions(self, limit: int = 10) -> list[Session]:
        """列出最近会话"""
        sessions = []
        for path in sorted(
            self.storage_path.glob("*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )[:limit]:
            sessions.append(self._load_session(path))
        return sessions
    
    def load_session(self, session_id: str) -> Session | None:
        """加载指定会话"""
        path = self.storage_path / f"{session_id}.json"
        if path.exists():
            self.current_session = self._load_session(path)
            return self.current_session
        return None
    
    def export_session(self, session_id: str, format: str = "json") -> str:
        """导出会话"""
        session = self.load_session(session_id)
        if not session:
            return ""
        
        if format == "json":
            return json.dumps(session.to_dict(), indent=2)
        elif format == "markdown":
            lines = [f"# Session: {session.id}", ""]
            lines.append(f"Created: {session.created_at}")
            lines.append(f"Updated: {session.updated_at}")
            lines.append("")
            
            for msg in session.messages:
                lines.append(f"## {msg.role.title()}")
                lines.append(f"Time: {msg.timestamp}")
                lines.append("")
                lines.append(msg.content)
                lines.append("")
            
            return "\n".join(lines)
        
        return ""
```

### 5.2 上下文压缩策略

```python
# src/zero_agent/session/compressor.py
"""上下文压缩策略"""

from dataclasses import dataclass
from typing import Any
import re

@dataclass
class CompressionConfig:
    """压缩配置"""
    max_tokens: int = 8000
    compress_threshold: float = 0.8
    keep_recent_turns: int = 4
    max_summary_tokens: int = 500

class ContextCompressor:
    """上下文压缩器"""
    
    def __init__(
        self, 
        llm: "LLMAdapter", 
        config: CompressionConfig
    ):
        self.llm = llm
        self.config = config
    
    def estimate_tokens(self, messages: list[dict]) -> int:
        """估算 token 数量"""
        total = 0
        for msg in messages:
            content = msg.get("content", "")
            # 粗略估算：英文 ~0.25 chars/token, 中文 ~0.5
            chinese_chars = len(re.findall(r'[一-鿿]', content))
            other_chars = len(content) - chinese_chars
            total += int(chinese_chars * 2 + other_chars * 0.25)
            total += 20  # 消息格式开销
        return total
    
    def should_compress(self, messages: list[dict]) -> bool:
        """判断是否需要压缩"""
        current = self.estimate_tokens(messages)
        threshold = self.config.max_tokens * self.config.compress_threshold
        return current >= threshold
    
    def compress(self, messages: list[dict]) -> list[dict]:
        """执行压缩"""
        if len(messages) <= self.config.keep_recent_turns:
            return messages
        
        # 分离旧消息和最近消息
        old_messages = messages[:-self.config.keep_recent_turns]
        recent_messages = messages[-self.config.keep_recent_turns:]
        
        if not old_messages:
            return messages
        
        # 生成摘要
        summary = self._generate_summary(old_messages)
        
        # 构建压缩后的消息列表
        return [
            {
                "role": "system",
                "content": f"[Previous conversation summary]\n{summary}"
            },
            *recent_messages
        ]
    
    def _generate_summary(self, messages: list[dict]) -> str:
        """生成对话摘要"""
        # 构建摘要提示
        prompt = self._build_summary_prompt(messages)
        
        # 调用 LLM 生成摘要
        response = self.llm.chat(
            [{"role": "user", "content": prompt}],
            options={"max_tokens": self.config.max_summary_tokens}
        )
        
        return response.content
    
    def _build_summary_prompt(self, messages: list[dict]) -> str:
        """构建摘要提示"""
        lines = [
            "Summarize the following conversation concisely.",
            "Include:",
            "- Key topics discussed",
            "- Important decisions made",
            "- Any code or commands executed",
            "- Current task status",
            "",
            "Keep the summary under 200 words.",
            "",
            "---",
            ""
        ]
        
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            
            # 简化工具调用结果
            if role == "tool":
                content = content[:500] + "..." if len(content) > 500 else content
            
            lines.append(f"[{role.upper()}]")
            lines.append(content)
            lines.append("")
        
        lines.append("---")
        lines.append("Summary:")
        
        return "\n".join(lines)
    
    def smart_compress(
        self, 
        messages: list[dict],
        keep_patterns: list[str] | None = None
    ) -> list[dict]:
        """智能压缩，保留重要内容"""
        keep_patterns = keep_patterns or [
            r"error",
            r"failed",
            r"important",
            r"todo",
            r"note:",
        ]
        
        # 找出需要保留的消息
        important_indices = set()
        for i, msg in enumerate(messages):
            content = msg.get("content", "").lower()
            for pattern in keep_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    important_indices.add(i)
                    break
        
        # 分离普通消息和重要消息
        normal_messages = []
        important_messages = []
        
        for i, msg in enumerate(messages):
            if i in important_indices:
                important_messages.append((i, msg))
            else:
                normal_messages.append(msg)
        
        # 压缩普通消息
        if normal_messages and len(normal_messages) > self.config.keep_recent_turns:
            compressed = self.compress(normal_messages)
        else:
            compressed = normal_messages
        
        # 合并
        result = compressed
        for idx, msg in important_messages:
            # 在正确位置插入重要消息
            pass  # 简化实现
        
        return result
```

## 六、TUI 界面实现

### 6.1 主应用类

```python
# src/zero_agent/tui/app.py
"""主应用类"""

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.widgets import Header, Footer

from zero_agent.config import Config
from zero_agent.tui.screens.main import MainScreen
from zero_agent.tui.widgets.header import StatusHeader
from zero_agent.tui.widgets.footer import CommandFooter

class ZeroAgentApp(App):
    """Zero Agent TUI 应用"""
    
    CSS_PATH = "styles/app.css"
    
    BINDINGS = [
        Binding("tab", "cycle_mode", "Cycle Mode"),
        Binding("ctrl+t", "cycle_lang", "Cycle Language"),
        Binding("ctrl+c", "cancel", "Cancel"),
        Binding("ctrl+l", "clear_screen", "Clear"),
        Binding("ctrl+d", "toggle_debug", "Debug"),
        Binding("f1", "show_help", "Help"),
        Binding("f5", "refresh", "Refresh"),
    ]
    
    def __init__(
        self, 
        config: Config,
        mode: str = "ask",
        lang: str = "en"
    ):
        super().__init__()
        self.config = config
        self.mode = mode
        self.lang = lang
        
        # 初始化组件
        self.llm = OllamaAdapter(config.llm)
        self.history = HistoryManager(config.history)
        self.security = EnhancedSecurityManager(config.security)
        self.skills = SkillLoader(config.skill_paths)
        self.mcp_client = MCPClient(config.mcp_servers)
        self.command_registry = CommandRegistry()
        self.session_manager = SessionManager()
        
        # 处理器
        self.tool_handler = ToolHandler(self)
        self.stream_handler = StreamHandler(self)
    
    def compose(self) -> ComposeResult:
        """构建界面"""
        yield StatusHeader()
        yield MainScreen()
        yield CommandFooter()
    
    def on_mount(self) -> None:
        """应用启动"""
        self.skills.load_all()
        self.load_session_history()
        self.update_status()
    
    def on_unmount(self) -> None:
        """应用退出"""
        self.session_manager.save_session()
    
    # === 动作处理 ===
    
    def action_cycle_mode(self) -> None:
        """循环切换模式"""
        modes = ["plan", "ask", "yolo"]
        idx = modes.index(self.mode)
        self.mode = modes[(idx + 1) % len(modes)]
        self.security.yolo = (self.mode == "yolo")
        self.update_status()
        self.notify(f"Mode: {self.mode}")
    
    def action_cycle_lang(self) -> None:
        """循环切换语言"""
        langs = ["en", "zh", "ja"]
        idx = langs.index(self.lang)
        self.lang = langs[(idx + 1) % len(langs)]
        self.update_status()
        self.notify(f"Language: {self.lang}")
    
    def action_cancel(self) -> None:
        """取消当前操作"""
        if self.stream_handler.is_streaming:
            self.stream_handler.cancel()
            self.notify("Cancelled", severity="warning")
    
    def action_clear_screen(self) -> None:
        """清屏"""
        self.query_one(MainScreen).clear_messages()
        self.notify("Screen cleared")
    
    def action_show_help(self) -> None:
        """显示帮助"""
        self.push_screen("help")
    
    # === 状态更新 ===
    
    def update_status(self) -> None:
        """更新状态栏"""
        header = self.query_one(StatusHeader)
        header.update(
            mode=self.mode,
            lang=self.lang,
            model=self.config.llm.model
        )
    
    # === 消息处理 ===
    
    def t(self, key: str, *args) -> str:
        """翻译文本"""
        texts = {
            "en": {
                "welcome": "Welcome to Zero Agent",
                "error": "Error: {}",
            },
            "zh": {
                "welcome": "欢迎使用 Zero Agent",
                "error": "错误: {}",
            },
            "ja": {
                "welcome": "Zero Agent へようこそ",
                "error": "エラー: {}",
            },
        }
        text = texts.get(self.lang, texts["en"]).get(key, key)
        if args:
            return text.format(*args)
        return text
    
    # === 历史管理 ===
    
    def load_session_history(self) -> None:
        """加载会话历史"""
        if session := self.session_manager.current_session:
            screen = self.query_one(MainScreen)
            for msg in session.messages:
                screen.add_message(msg)
    
    def add_to_history(self, role: str, content: str, **kwargs) -> None:
        """添加到历史"""
        msg = Message(
            id=self._generate_msg_id(),
            role=role,
            content=content,
            **kwargs
        )
        self.session_manager.current_session.add_message(msg)
        
        # 检查压缩
        if self.history.should_compress():
            self.history.compress(self.llm)


def run_tui(config: Config, mode: str, lang: str) -> None:
    """启动 TUI"""
    app = ZeroAgentApp(config, mode, lang)
    app.run()
```

### 6.2 消息列表组件

```python
# src/zero_agent/tui/widgets/message_list.py
"""消息列表组件"""

from textual.widget import Widget
from textual.containers import VerticalScroll
from textual.message import Message
from typing import Any

class MessageList(VerticalScroll):
    """可滚动的消息列表"""
    
    DEFAULT_CSS = """
    MessageList {
        height: 1fr;
        padding: 1;
    }
    
    MessageList:focus {
        outline: none;
    }
    """
    
    def __init__(self):
        super().__init__()
        self._message_count = 0
    
    def add_message(self, message: "Message") -> None:
        """添加消息"""
        widget = self._create_message_widget(message)
        self.mount(widget)
        self._message_count += 1
        # 滚动到底部
        self.call_after_refresh(self.scroll_end, animate=False)
    
    def _create_message_widget(self, message: "Message") -> Widget:
        """创建消息组件"""
        if message.role == "user":
            return UserMessageWidget(message)
        elif message.role == "assistant":
            return AssistantMessageWidget(message)
        elif message.role == "tool":
            return ToolMessageWidget(message)
        else:
            return SystemMessageWidget(message)
    
    def clear(self) -> None:
        """清空消息"""
        self.remove_children()
        self._message_count = 0
    
    def update_last_message(self, content: str) -> None:
        """更新最后一条消息（用于流式输出）"""
        children = list(self.children)
        if children:
            last = children[-1]
            if isinstance(last, AssistantMessageWidget):
                last.update_content(content)


class UserMessageWidget(Widget):
    """用户消息组件"""
    
    DEFAULT_CSS = """
    UserMessageWidget {
        margin: 1 0;
        padding: 1;
        background: $surface-1;
        border-left: thick $primary;
    }
    
    UserMessageWidget .role {
        color: $primary;
        text-style: bold;
    }
    """
    
    def __init__(self, message: "Message"):
        self.message = message
        super().__init__()
    
    def compose(self):
        from textual.widgets import Static
        yield Static(f"[You]", classes="role")
        yield Static(self.message.content, classes="content")


class AssistantMessageWidget(Widget):
    """助手消息组件"""
    
    DEFAULT_CSS = """
    AssistantMessageWidget {
        margin: 1 0;
        padding: 1;
        background: $surface-2;
        border-left: thick $success;
    }
    
    AssistantMessageWidget .role {
        color: $success;
        text-style: bold;
    }
    """
    
    def __init__(self, message: "Message"):
        self.message = message
        self._content = message.content
        super().__init__()
    
    def compose(self):
        from textual.widgets import Static
        yield Static(f"[Assistant]", classes="role")
        self.content_widget = Static(self._content, classes="content")
        yield self.content_widget
    
    def update_content(self, content: str) -> None:
        """更新内容（流式输出）"""
        self._content = content
        self.content_widget.update(content)


class ToolMessageWidget(Widget):
    """工具调用消息组件"""
    
    DEFAULT_CSS = """
    ToolMessageWidget {
        margin: 1 0;
        padding: 1;
        background: $surface-3;
        border-left: thick $warning;
    }
    
    ToolMessageWidget .tool-name {
        color: $warning;
        text-style: bold;
    }
    
    ToolMessageWidget .command {
        background: $surface-0;
        padding: 0 1;
    }
    
    ToolMessageWidget .result {
        color: $text-muted;
    }
    """
    
    def __init__(self, message: "Message"):
        self.message = message
        super().__init__()
    
    def compose(self):
        from textual.widgets import Static
        tool_name = self.message.metadata.get("tool_name", "unknown")
        command = self.message.metadata.get("command", "")
        
        yield Static(f"[Tool: {tool_name}]", classes="tool-name")
        if command:
            yield Static(f"$ {command}", classes="command")
        yield Static(self.message.content[:500], classes="result")
```

### 6.3 输入组件

```python
# src/zero_agent/tui/widgets/input_box.py
"""输入组件"""

from textual.widget import Widget
from textual.widgets import Input
from textual.containers import Horizontal
from textual.message import Message

class InputBox(Widget):
    """输入框组件"""
    
    DEFAULT_CSS = """
    InputBox {
        dock: bottom;
        height: auto;
        background: $surface-0;
        padding: 1;
    }
    
    InputBox Input {
        width: 1fr;
    }
    
    InputBox .mode-indicator {
        width: auto;
        min-width: 8;
        padding: 0 1;
        text-align: center;
    }
    """
    
    class Submitted(Message):
        """提交消息事件"""
        def __init__(self, text: str):
            self.text = text
            super().__init__()
    
    def __init__(self, mode: str = "ask"):
        self.mode = mode
        super().__init__()
    
    def compose(self):
        from textual.widgets import Static
        yield Static(f"[{self.mode}]", classes="mode-indicator")
        self.input = Input(placeholder="Type a message or /command...", id="main-input")
        yield self.input
    
    def on_mount(self) -> None:
        """挂载时聚焦输入框"""
        self.input.focus()
    
    def on_input_submitted(self, event: Input.Submitted) -> None:
        """处理输入提交"""
        if event.value.strip():
            self.post_message(self.Submitted(event.value))
            self.input.value = ""
    
    def update_mode(self, mode: str) -> None:
        """更新模式"""
        self.mode = mode
        self.query_one(".mode-indicator", Static).update(f"[{mode}]")
```

### 6.4 Textual CSS 样式

```css
/* src/zero_agent/tui/styles/app.css */

/* 全局样式 */
ZeroAgentApp {
    background: $surface;
    color: $text;
}

/* Header 样式 */
StatusHeader {
    dock: top;
    height: 3;
    background: $surface-1;
    border-bottom: solid $primary;
    padding: 0 2;
}

StatusHeader .title {
    text-style: bold;
    color: $primary;
}

StatusHeader .status-item {
    margin: 0 2;
}

/* Footer 样式 */
CommandFooter {
    dock: bottom;
    height: 2;
    background: $surface-1;
    border-top: solid $primary;
}

CommandFooter .binding {
    margin: 0 2;
}

/* 主屏幕 */
MainScreen {
    layout: vertical;
}

/* 消息列表 */
MessageList {
    height: 1fr;
    overflow-y: scroll;
}

/* 代码块样式 */
.code-block {
    background: $surface-2;
    padding: 1;
    margin: 1 0;
    border: round $surface-3;
}

/* 工具调用样式 */
.tool-pending {
    color: $warning;
}

.tool-running {
    color: $primary;
    text-style: blink;
}

.tool-success {
    color: $success;
}

.tool-error {
    color: $error;
}

/* 权限弹窗 */
PermissionScreen {
    align: center middle;
}

.permission-dialog {
    width: 60;
    height: auto;
    background: $surface-2;
    border: thick $warning;
    padding: 2;
}

.permission-dialog .title {
    text-style: bold;
    text-align: center;
    margin-bottom: 1;
}

.permission-dialog .risk-warning {
    color: $error;
    background: $surface-1;
    padding: 1;
    margin: 1 0;
}

.permission-dialog .buttons {
    align: center middle;
    height: auto;
    margin-top: 1;
}

/* 响应式布局 */
@media (max-width: 80) {
    StatusHeader {
        height: 2;
    }
    
    .permission-dialog {
        width: 100%;
    }
}
```

## 七、MCP 集成设计

### 7.1 MCP 客户端增强

```python
# src/zero_agent/mcp/client_v2.py
"""增强的 MCP 客户端"""

import asyncio
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable
from pathlib import Path
import json

@dataclass
class MCPServerConfig:
    """MCP Server 配置"""
    name: str
    command: str
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    auto_connect: bool = True
    timeout: int = 30

@dataclass
class MCPTool:
    """MCP 工具"""
    name: str
    description: str
    server_name: str
    input_schema: dict
    handler: Callable | None = None

class EnhancedMCPClient:
    """增强的 MCP 客户端"""
    
    def __init__(self):
        self.servers: dict[str, MCPServerConfig] = {}
        self.sessions: dict[str, "ClientSession"] = {}
        self.tools: dict[str, MCPTool] = {}
        self._connection_status: dict[str, str] = {}
    
    def load_config(self, servers_config: dict[str, Any]) -> None:
        """加载服务器配置"""
        for name, config in servers_config.items():
            self.servers[name] = MCPServerConfig(
                name=name,
                command=config.get("command", ""),
                args=config.get("args", []),
                env=config.get("env", {}),
                auto_connect=config.get("auto_connect", True),
                timeout=config.get("timeout", 30)
            )
    
    async def connect_all(self) -> dict[str, bool]:
        """连接所有服务器"""
        results = {}
        for name, server in self.servers.items():
            if server.auto_connect:
                results[name] = await self.connect_server(name)
        return results
    
    async def connect_server(self, name: str) -> bool:
        """连接单个服务器"""
        server = self.servers.get(name)
        if not server:
            return False
        
        try:
            self._connection_status[name] = "connecting"
            
            # 创建连接
            session = await self._create_session(server)
            self.sessions[name] = session
            
            # 获取工具列表
            tools = await self._fetch_tools(name, session)
            for tool in tools:
                self.tools[tool.name] = tool
            
            self._connection_status[name] = "connected"
            return True
            
        except Exception as e:
            self._connection_status[name] = f"error: {e}"
            return False
    
    async def disconnect_server(self, name: str) -> None:
        """断开服务器"""
        if session := self.sessions.pop(name, None):
            await session.close()
        
        # 移除相关工具
        self.tools = {
            k: v for k, v in self.tools.items() 
            if v.server_name != name
        }
        self._connection_status[name] = "disconnected"
    
    async def call_tool(
        self, 
        tool_name: str, 
        arguments: dict[str, Any]
    ) -> tuple[bool, str]:
        """调用工具"""
        tool = self.tools.get(tool_name)
        if not tool:
            return False, f"Tool not found: {tool_name}"
        
        session = self.sessions.get(tool.server_name)
        if not session:
            return False, f"Server not connected: {tool.server_name}"
        
        try:
            result = await asyncio.wait_for(
                session.call_tool(tool_name, arguments),
                timeout=self.servers[tool.server_name].timeout
            )
            
            content = str(result.content)
            is_error = getattr(result, "isError", False)
            
            return not is_error, content
            
        except asyncio.TimeoutError:
            return False, f"Tool call timed out: {tool_name}"
        except Exception as e:
            return False, f"Tool call error: {e}"
    
    def get_tool_definitions(self) -> list[dict]:
        """获取工具定义（供 LLM）"""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.input_schema.get("properties", {}),
            }
            for tool in self.tools.values()
        ]
    
    def get_status(self) -> dict[str, str]:
        """获取连接状态"""
        return self._connection_status.copy()
```

### 7.2 MCP 工具发现

```python
# src/zero_agent/mcp/discovery.py
"""MCP 工具发现和管理"""

class MCPToolManager:
    """MCP 工具管理器"""
    
    def __init__(self, client: "EnhancedMCPClient"):
        self.client = client
        self._tool_handlers: dict[str, Callable] = {}
    
    def register_handler(
        self, 
        tool_name: str, 
        handler: Callable
    ) -> None:
        """注册自定义工具处理器"""
        self._tool_handlers[tool_name] = handler
    
    async def execute(
        self, 
        tool_name: str, 
        arguments: dict[str, Any]
    ) -> str:
        """执行工具"""
        # 检查自定义处理器
        if handler := self._tool_handlers.get(tool_name):
            return await handler(arguments)
        
        # 使用 MCP 客户端
        success, result = await self.client.call_tool(tool_name, arguments)
        
        if not success:
            raise ToolExecutionError(result)
        
        return result
    
    def list_tools(self) -> list[dict]:
        """列出所有工具"""
        tools = []
        
        for name, tool in self.client.tools.items():
            tools.append({
                "name": name,
                "description": tool.description,
                "server": tool.server_name,
                "schema": tool.input_schema,
            })
        
        return tools
    
    def search_tools(self, query: str) -> list[dict]:
        """搜索工具"""
        query = query.lower()
        return [
            t for t in self.list_tools()
            if query in t["name"].lower() 
            or query in t["description"].lower()
        ]
```

## 八、实现路线图

### Phase 1: 基础 TUI 框架 (1-2 周)

1. 创建 Textual 应用骨架
2. 实现基础布局（Header, MessageList, Input, Footer）
3. 集成现有的 Agent 逻辑
4. 添加基本键绑定

### Phase 2: 核心交互 (2-3 周)

1. 实现流式输出显示
2. 实现工具调用处理
3. 实现权限确认弹窗
4. 实现斜杠命令系统

### Phase 3: 会话管理 (1-2 周)

1. 实现会话持久化
2. 实现历史压缩
3. 实现会话恢复
4. 实现导出功能

### Phase 4: MCP 增强 (1-2 周)

1. 增强连接管理
2. 实现工具发现
3. 实现连接状态显示
4. 添加 MCP 命令

### Phase 5: 优化和测试 (1 周)

1. 性能优化
2. 边界情况处理
3. 文档完善
4. 测试覆盖

## 九、关键代码示例

### 完整的应用启动示例

```python
# src/zero_agent/__main__.py
"""应用入口"""

import click
from zero_agent.config import load_config
from zero_agent.tui.app import ZeroAgentApp, run_tui

@click.command()
@click.option("--config", "-c", type=click.Path(), help="Config file path")
@click.option("--mode", "-m", type=click.Choice(["plan", "ask", "yolo"]), default="ask")
@click.option("--lang", "-l", type=click.Choice(["en", "zh", "ja"]), default="en")
@click.option("--no-tui", is_flag=True, help="Run without TUI (REPL mode)")
def main(config: str | None, mode: str, lang: str, no_tui: bool):
    """Zero Agent - CLI Agent with MCP, Skills, and Security Control"""
    cfg = load_config(config)
    
    if no_tui:
        # 传统 REPL 模式
        from zero_agent.agent import Agent
        agent = Agent(cfg, mode=mode, lang=lang)
        agent.start_repl()
    else:
        # TUI 模式
        run_tui(cfg, mode, lang)

if __name__ == "__main__":
    main()
```

---

这份设计文档为零-agent 项目提供了完整的 TUI 架构设计，涵盖了交互流程、权限系统、斜杠命令、会话管理和 MCP 集成等核心功能。设计参考了 Claude Code CLI 的最佳实践，同时针对小模型优化做了特别考虑。
