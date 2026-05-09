# Spark

A minimal **harness** optimized for **small local models** (gemma3:4b, qwen2.5:3b).

> **Agency comes from the model, not the code.**
> 
> Harness = Tools + Knowledge + Observation + Action Interfaces + Permissions

## Why Harness, Not Agent?

Traditional "agent" frameworks try to embed intelligence in code. This is wrong.

**The model provides agency.** The harness provides:

| Component | Description | Spark Implementation |
|-----------|-------------|------------------------------|
| **Tools** | Capabilities the model can use | `run_shell`, `search` |
| **Knowledge** | Context and skills | Dynamic prompts, skill loader |
| **Observation** | See the world | File operations, command output |
| **Action Interfaces** | Execute changes | Shell commands, file operations |
| **Permissions** | Safety boundaries | Mode system, path trust, risk detection |

## Key Design Principles

### 1. Model-Centric, Not Code-Centric

```
❌ Wrong:  Code tries to be "smart", makes decisions for the model
✅ Right:  Code is dumb, provides clear signals, model decides
```

Example - Tool Result:
```
[TOOL RESULT: run_shell]
STATUS: FAILURE ✗
ERROR: Permission denied
[ACTION REQUIRED: Acknowledge failure]
[END RESULT]
```

The harness doesn't decide what to do. It provides **clear, structured information** and lets the model decide.

### 2. Explicit Over Implicit

Small models struggle with implicit signals. The harness makes everything explicit:

| Implicit (Bad) | Explicit (Good) |
|----------------|-----------------|
| `return "Error: file not found"` | `STATUS: FAILURE ✗ ERROR: file not found` |
| `if output contains "error"` | `if success == False` |
| `# model should understand` | `[ACTION REQUIRED: ...]` |

### 3. Trust Explicit Flags, Not Patterns

```python
# ❌ Wrong: Infer from output patterns
if "error" in output:
    return FAILURE

# ✅ Right: Trust explicit flags
if result["success"] is False:
    return FAILURE
if result["returncode"] != 0:
    return FAILURE
```

Why? `grep "error:" file` returns "error:" in output but is successful.

### 4. Token Efficiency

Small models have limited context. Every token matters:

| Technique | Implementation |
|-----------|----------------|
| Output truncation | Max 1000 chars |
| Prompt compression | Context-aware, minimal |
| History summarization | Compress old messages |
| Skill lazy-loading | Load only relevant skills |

### 5. Cross-Platform by Design

No shell dependencies. Pure Python:

```python
# ❌ Wrong: Shell dependency
subprocess.run(["ls", "-la"])

# ✅ Right: Pure Python
pathlib.Path(".").iterdir()
```

Works identically on Windows, Linux, macOS.

## Features

| Feature | Description |
|---------|-------------|
| **Hallucination Prevention** | Structured results, explicit status markers |
| **Web Search** | DuckDuckGo integration (no API key) |
| **Security** | Mode system, path trust, risk detection |
| **Multi-language** | English, 中文, 日本語 |
| **Token Optimized** | Truncation, compression, lazy loading |

## The Harness Equation

```
┌─────────────────────────────────────────────────────────────┐
│                        SPARK                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │  TOOLS   │  │ KNOWLEDGE│  │OBSERVATION│  │  ACTION  │    │
│  │          │  │          │  │          │  │          │    │
│  │run_shell │  │ prompts  │  │   fs/    │  │  shell/  │    │
│  │  search  │  │ skills   │  │operations│  │ builtin  │    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘    │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                    PERMISSIONS                        │   │
│  │                                                       │   │
│  │  Mode: plan/ask/yolo  │  Path Trust  │  Risk Detect  │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                  FEEDBACK LOOP                        │   │
│  │                                                       │   │
│  │  Tool Result → Verifier → Structured Output → Model  │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                        ┌──────────┐
                        │  MODEL   │
                        │(gemma3)  │
                        │(qwen2.5) │
                        └──────────┘
                              │
                              ▼
                        Agency emerges
```

## Installation

### 1. Install Ollama

```bash
# Linux/macOS
curl -fsSL https://ollama.com/install.sh | sh

# Start Ollama
ollama serve

# Download a small model
ollama pull gemma3:4b
# or
ollama pull qwen2.5:3b
```

### 2. Install Spark

```bash
git clone https://github.com/adam-ikari/spark.git
cd spark
uv sync
```

## Development

### Run in Development Environment

```bash
# Clone and enter project
git clone https://github.com/adam-ikari/spark.git
cd spark

# Run directly without installation
uv run python -m spark --trust --once "your prompt"

# Run tests
uv run pytest tests/ -v

# Run specific tests
uv run pytest tests/test_builtin.py -v
```

### Install for Development

```bash
# Install dependencies with uv (recommended)
uv sync

# Or traditional pip
pip install -e .
```

### Project Structure

```
spark/
├── src/spark/          # Source code (src layout)
│   ├── __init__.py
│   ├── __main__.py     # Entry point for python -m
│   ├── agent.py        # Core loop
│   └── ...
├── tests/              # Test files
├── pyproject.toml      # Project config
└── README.md
```

## Usage

### REPL Mode (Interactive)

```bash
# Start interactive REPL
spark

# With options
spark --mode yolo --lang zh
spark --trust  # Skip trust prompt
```

### Single Execution

```bash
# Run once and exit
spark --once "list files in current directory"
spark --once "search python tutorials"
spark -o "read README.md" --mode plan
```

### TUI Mode (Terminal UI)

```bash
spark --tui
spark -t
```

### CLI Options

| Option | Short | Description |
|--------|-------|-------------|
| `--once "prompt"` | `-o` | Run once with prompt and exit |
| `--mode MODE` | `-m` | Mode: plan, ask, yolo |
| `--lang LANG` | `-l` | Language: en, zh, ja |
| `--tui` | `-t` | Launch TUI interface |
| `--trust` | | Trust current directory |
| `--config PATH` | `-c` | Config file path |
| `--version` | | Show version |
| `--help` | | Show help |

### REPL Commands

| Command | Description |
|---------|-------------|
| `/exit` | Exit REPL |
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
| `Tab` | Cycle modes |

## Modes

| Mode | Description |
|------|-------------|
| **plan** | Read-only, all writes denied |
| **ask** | Confirm based on config |
| **yolo** | Auto-run safe operations |

## Project Structure

```
src/spark/
├── agent.py            # Core loop (dumb, just orchestration)
├── cli.py              # Entry point
├── prompts.py          # Dynamic prompts (knowledge)
├── fs/                 # File operations (observation)
├── search/             # Web search (observation)
├── feedback/           # Result verification (explicit signals)
├── security/           # Permissions (safety)
├── builtin/            # Tools (capabilities)
├── mcp/                # MCP client (external tools)
├── skills/             # Skill loader (knowledge)
└── memory/             # Memory (context)
```

## License

MIT