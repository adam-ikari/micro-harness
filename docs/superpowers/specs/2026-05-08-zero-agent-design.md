# Zero Agent 设计文档

## 概述

一个最小化的 CLI Agent，支持 MCP、Skills、安全控制和 YOLO 模式，对小模型（如 Gemma 4）友好。

## 核心需求

- **CLI 工具**: REPL 模式 + 单次执行模式
- **MCP Client**: 连接外部 MCP server 获取工具
- **Skills**: 从文件系统加载 .md 文件作为 skill prompt
- **安全控制**: 工具调用权限 + 高风险操作拦截
- **YOLO 模式**: 只对高风险操作确认，普通操作自动执行
- **LLM**: 使用 Ollama 本地模型
- **小模型友好**: 精简 prompt、压缩历史、限制上下文

## 项目结构

```
zero-agent/
├── src/zero_agent/
│   ├── __init__.py
│   ├── cli.py              # CLI 入口，REPL/单次执行
│   ├── agent.py            # Agent 核心，对话循环
│   ├── llm.py              # Ollama API 适配器
│   ├── history.py          # 对话历史管理 + 摘要压缩
│   ├── mcp/
│   │   ├── __init__.py
│   │   ├── client.py       # MCP 客户端连接管理
│   │   └── types.py        # MCP 相关类型定义
│   ├── skills/
│   │   ├── __init__.py
│   │   └── loader.py       # Skills 加载器
│   ├── security/
│   │   ├── __init__.py
│   │   ├── permission.py   # 权限控制
│   │   └── risk_detector.py # 风险操作检测
│   ├── builtin/
│   │   ├── __init__.py
│   │   └── shell.py        # Shell 工具（唯一内置工具）
│   └── config.py           # 配置管理
├── config.yaml             # 默认配置文件
└── pyproject.toml
```

## 架构设计

### 分层架构

```
┌────────────────────────────────────────────────────────────┐
│                         CLI Layer                           │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐   │
│  │  REPL Mode   │  │  Once Mode   │  │  Arg Parser     │   │
│  └──────────────┘  └──────────────┘  └─────────────────┘   │
└────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────┐
│                        Agent Core                           │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐   │
│  │ Chat Loop    │  │ History Mgr  │  │ Tool Dispatcher │   │
│  └──────────────┘  └──────────────┘  └─────────────────┘   │
└────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────────┐
│   LLM Adapter   │ │  Skills Loader  │ │   Security Layer    │
│  ┌───────────┐  │ │  ┌───────────┐  │ │  ┌───────────────┐  │
│  │  Ollama   │  │ │  │ Global    │  │ │  │ Permission    │  │
│  │  API      │  │ │  │ Skills    │  │ │  │ Manager       │  │
│  └───────────┘  │ │  ├───────────┤  │ │  ├───────────────┤  │
│                 │ │  │ Project   │  │ │  │ Risk Detector │  │
│                 │ │  │ Skills    │  │ │  └───────────────┘  │
│                 │ │  └───────────┘  │ │                     │
└─────────────────┘ └─────────────────┘ └─────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────┐
│                      Tool Sources                           │
│  ┌─────────────────┐  ┌─────────────────────────────────┐  │
│  │  Builtin Tools  │  │        MCP Client               │  │
│  │  ┌───────────┐  │  │  ┌───────────┐  ┌───────────┐   │  │
│  │  │ run_shell │  │  │  │ server A  │  │ server B  │   │  │
│  │  └───────────┘  │  │  └───────────┘  └───────────┘   │  │
│  └─────────────────┘  └─────────────────────────────────┘  │
└────────────────────────────────────────────────────────────┘
```

## 组件详细设计

### 1. CLI 层 (`cli.py`)

入口点，负责：
- 解析命令行参数
- 加载配置
- 初始化 Agent
- 选择执行模式（REPL 或单次）

```python
def main():
    args = parse_args()
    config = load_config(args.config)
    agent = Agent(config, yolo=args.yolo)

    if args.once:
        result = agent.run_once(args.prompt)
        print(result)
    else:
        agent.start_repl()
```

命令行参数：
- `--config <path>`: 指定配置文件
- `--once "prompt"`: 单次执行模式
- `--yolo`: 开启 YOLO 模式

### 2. Agent 核心 (`agent.py`)

核心职责：
- 对话循环管理
- 消息构建（system prompt + skills + 历史 + 用户输入）
- 工具调用调度
- 响应处理

```python
class Agent:
    def __init__(self, config, yolo=False):
        self.llm = OllamaAdapter(config.llm)
        self.mcp_client = MCPClient(config.mcp_servers)
        self.skills = SkillLoader(config.skill_paths)
        self.security = SecurityManager(config.security, yolo=yolo)
        self.history = HistoryManager(config.history)
        self.tools = ToolRegistry()

    def run_once(self, prompt: str) -> str:
        """单次执行"""

    def start_repl(self):
        """启动交互式对话"""

    def _build_messages(self, user_input: str) -> list:
        """构建发送给 LLM 的消息"""

    def _process_response(self, response) -> str:
        """处理 LLM 响应，执行工具调用"""

    def _handle_tool_call(self, tool_name: str, args: dict) -> Any:
        """处理单个工具调用"""
```

### 3. LLM 适配器 (`llm.py`)

封装 Ollama API：

```python
class OllamaAdapter:
    def __init__(self, config):
        self.base_url = config.get("base_url", "http://localhost:11434")
        self.model = config.get("model", "gemma3:4b")
        self.num_ctx = config.get("num_ctx", 8192)
        self.num_predict = config.get("num_predict", 2048)

    def chat(self, messages: list, tools: list = None) -> Response:
        """发送对话请求"""

    def generate_summary(self, messages: list) -> str:
        """生成历史摘要"""
```

### 4. 历史管理 (`history.py`)

对话历史管理 + 摘要压缩：

```python
class HistoryManager:
    def __init__(self, config):
        self.messages = []
        self.max_tokens = config.get("max_tokens", 8000)
        self.compress_threshold = config.get("compress_threshold", 0.8)

    def add(self, role: str, content: str):
        """添加消息到历史"""

    def get_token_count(self) -> int:
        """估算当前历史的 token 数"""

    def should_compress(self) -> bool:
        """判断是否需要压缩"""

    def compress(self, llm: OllamaAdapter):
        """生成摘要替换旧消息"""
```

### 5. MCP 客户端 (`mcp/client.py`)

连接外部 MCP server：

```python
class MCPClient:
    def __init__(self, servers_config: dict):
        self.connections = {}
        self.tools = []

    async def connect_all(self):
        """连接所有配置的 MCP server"""

    async def call_tool(self, name: str, args: dict) -> Any:
        """调用工具"""

    def get_tool_definitions(self) -> list:
        """获取所有工具定义（供 LLM 使用）"""
```

### 6. Skills 加载器 (`skills/loader.py`)

从文件系统加载 skills：

```python
class SkillLoader:
    def __init__(self, skill_paths: list):
        self.skills = {}

    def load_all(self):
        """从配置路径加载所有 .md 文件"""

    def get_skill(self, name: str) -> str:
        """获取指定 skill 内容"""

    def get_all_skills_prompt(self) -> str:
        """拼接所有 skills 为 prompt"""
```

Skills 目录结构：
```
~/.zero-agent/skills/          # 全局 skills
./.zero-agent/skills/          # 项目 skills（优先级更高）
```

Skill 文件格式：
```markdown
---
name: code-review
description: Review code for quality and bugs
trigger: when user asks to review code
---

You are a code reviewer. Focus on:
- Code quality
- Potential bugs
- Performance issues
```

### 7. 安全控制层 (`security/`)

#### 权限管理 (`permission.py`)

```python
class PermissionManager:
    def __init__(self, config):
        self.permissions = config.get("permissions", {})

    def check(self, tool_name: str, args: dict) -> Decision:
        """检查工具调用权限"""
        # 返回: ALLOW, DENY, CONFIRM
```

#### 风险检测 (`risk_detector.py`)

```python
class RiskDetector:
    def __init__(self, config):
        self.blocked_commands = config.get("blocked_commands", [])
        self.confirm_patterns = config.get("confirm_patterns", [])

    def is_blocked(self, command: str) -> bool:
        """检查是否为禁止命令"""

    def needs_confirm(self, command: str) -> bool:
        """检查是否需要确认"""
```

#### 安全管理器 (`security/__init__.py`)

```python
class SecurityManager:
    def __init__(self, config, yolo=False):
        self.yolo = yolo
        self.permissions = PermissionManager(config)
        self.risk_detector = RiskDetector(config)

    def check(self, tool_name: str, args: dict) -> Decision:
        if self.yolo:
            # YOLO 模式：只对高风险确认
            if self.risk_detector.needs_confirm(args.get("command", "")):
                return Decision.CONFIRM
            return Decision.ALLOW

        # 正常模式
        if self.risk_detector.is_blocked(args.get("command", "")):
            return Decision.DENY
        return self.permissions.check(tool_name, args)
```

### 8. 内置工具 (`builtin/`)

仅提供 `run_shell` 工具：

```python
# shell.py
TOOLS = [
    {
        "name": "run_shell",
        "description": "Execute shell command. Use for file operations, network requests, and any system tasks.",
        "parameters": {
            "command": "Shell command to execute",
            "timeout": "Timeout in seconds (default 30)"
        }
    }
]

def execute(command: str, timeout: int = 30) -> dict:
    """执行 shell 命令，返回结果"""
```

所有操作通过 shell 实现：
- 读文件: `cat <path>`
- 写文件: `echo "content" > <path>`
- 列目录: `ls -la <path>`
- HTTP GET: `curl <url>`
- HTTP POST: `curl -X POST -d "data" <url>`
- 执行 Python: `python -c "code"`

### 9. 配置管理 (`config.py`)

```python
@dataclass
class Config:
    llm: LLMConfig
    mcp_servers: dict
    skill_paths: list
    security: SecurityConfig
    history: HistoryConfig

def load_config(path: str = None) -> Config:
    """加载配置，优先级：命令行 > 项目 > 全局 > 默认"""

def find_config_files() -> list:
    """查找配置文件"""
```

## 配置文件格式

```yaml
# LLM 配置
llm:
  base_url: "http://localhost:11434"
  model: "gemma3:4b"
  num_ctx: 8192
  num_predict: 2048

# MCP Servers
mcp_servers:
  filesystem:
    command: npx
    args: ["-y", "@modelcontextprotocol/server-filesystem", "./"]

# Skills 路径
skill_paths:
  - "~/.zero-agent/skills"
  - "./.zero-agent/skills"

# 安全配置
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

# 历史管理
history:
  max_tokens: 8000
  compress_threshold: 0.8
```

## 数据流

```
用户输入 → CLI 解析 → 加载配置/Skills/连接MCP → 构建消息 → 调用 LLM
    → LLM 返回响应 → 工具调用? → 安全检查 → 执行工具 → 更新历史
    → 压缩历史? → 输出结果 → (REPL: 继续循环)
```

安全检查决策：
- **ALLOW**: 直接执行
- **DENY**: 拒绝执行，返回错误信息
- **CONFIRM**: 等待用户确认后执行或拒绝

## 小模型优化策略

| 优化点 | 实现 |
|--------|------|
| Prompt 精简 | Skills 按需加载，非全部注入 |
| 工具描述精简 | 仅传递 name + description + 必要参数 |
| 历史压缩 | 达到阈值时生成摘要替换旧消息 |
| 上下文限制 | 可配置 `num_ctx` |
| 输出限制 | 可配置 `num_predict` |
| 单一工具 | 仅 `run_shell`，减少工具选择复杂度 |