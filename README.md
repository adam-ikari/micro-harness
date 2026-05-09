# Micro Harness

A minimal **harness** optimized for **small local models** (gemma3:4b, qwen2.5:3b).

> **Agency comes from the model, not the code.**
> 
> Harness = Tools + Knowledge + Observation + Action Interfaces + Permissions

## Why Harness, Not Agent?

Traditional "agent" frameworks try to embed intelligence in code. This is wrong.

**The model provides agency.** The harness provides:

| Component | Description | Micro Harness Implementation |
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
│                        MICRO HARNESS                         │
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

```bash
git clone https://github.com/yourname/micro-harness.git
cd micro-harness
pip install -e .
```

## Usage

```bash
# REPL mode
micro-harness

# Single execution
micro-harness --once "list files"

# With mode
micro-harness --mode yolo
```

## Modes

| Mode | Description |
|------|-------------|
| **plan** | Read-only, all writes denied |
| **ask** | Confirm based on config |
| **yolo** | Auto-run safe operations |

## Project Structure

```
src/micro_harness/
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