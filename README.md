# Zero Agent

A minimal CLI agent with MCP, Skills, and security control, optimized for small models.

## Features

- **TUI Interface**: Modern terminal UI with Textual
- **CLI Modes**: REPL and single-shot execution
- **Mode Switching**: Tab to cycle: plan → ask → yolo
- **Multi-language**: Commands /en, /zh, /ja
- **MCP Client**: Connect to external MCP servers
- **Skills**: Load skill prompts from `.md` files
- **Security**: Permission control + risk detection
- **Small Model Friendly**: Compressed prompts, history summarization

## Modes

| Mode | Description |
|------|-------------|
| **plan** | Read-only mode, all write operations are denied |
| **ask** | Confirm based on config (default) |
| **yolo** | Auto-run safe operations, only confirm high-risk |

Press **Tab** in TUI to cycle modes.

## Languages

| Lang | Description |
|------|-------------|
| **en** | English |
| **zh** | 中文 |
| **ja** | 日本語 |

Use commands `/en`, `/zh`, `/ja` to switch.

## Installation

```bash
uv sync
```

## Usage

### TUI Mode (Recommended)

```bash
uv run zero-agent --tui
uv run zero-agent -t
```

### REPL Mode

```bash
uv run zero-agent
```

### Single Execution

```bash
uv run zero-agent --once "Your prompt"
```

### Start with Mode

```bash
uv run zero-agent --mode yolo
uv run zero-agent -m plan -l zh
```

## TUI Shortcuts

| Key | Action |
|-----|--------|
| `Tab` | Cycle mode |
| `Ctrl+L` | Clear screen |
| `Ctrl+C` | Quit |

## Commands

| Command | Description |
|---------|-------------|
| `/exit` | Exit |
| `/clear` | Clear history |
| `/help` | Show help |
| `/mode` | Show current mode |
| `/lang` | Show current language |
| `/plan` | Switch to plan mode |
| `/ask` | Switch to ask mode |
| `/yolo` | Switch to yolo mode |
| `/en` | Switch to English |
| `/zh` | Switch to 中文 |
| `/ja` | Switch to 日本語 |

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

## Project Structure

```
src/zero_agent/
├── __init__.py
├── cli.py              # CLI entry point
├── agent.py            # Core agent (REPL)
├── llm.py              # Ollama adapter
├── history.py          # History management
├── config.py           # Configuration
├── tui/                # TUI interface
│   ├── app.py          # Main application
│   ├── widgets/        # UI components
│   ├── screens/        # Modal screens
│   └── styles/         # CSS styles
├── mcp/                # MCP client
├── skills/             # Skills loader
├── security/           # Security layer
└── builtin/            # Built-in tools
```
