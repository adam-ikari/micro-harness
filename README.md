# Zero Agent

A minimal CLI agent optimized for **small local models** (gemma3:4b, qwen2.5:3b).

## Key Features

- **Small Model Optimized**: Compressed prompts, token limits, hallucination prevention
- **Cross-Platform**: Pure Python implementation, Windows-friendly
- **Web Search**: DuckDuckGo integration (no API key required)
- **Security**: Permission control + risk detection + path trust system
- **Multi-language**: English, 中文, 日本語

## Why Small Models?

Small models (3-4B parameters) are:
- **Fast**: Run locally on consumer hardware
- **Private**: No data sent to external servers
- **Free**: No API costs

But they have limitations:
- Limited context window
- May hallucinate tool success
- Need explicit, structured feedback

Zero Agent addresses these with:
- Token-limited output (1000 chars max)
- Structured tool results: `[TOOL RESULT] STATUS: SUCCESS/FAILURE ✓/✗`
- Anti-hallucination prompts: "IMPORTANT: The tool FAILED. Do NOT proceed."

## Installation

```bash
# Clone
git clone https://github.com/yourname/zero-agent.git
cd zero-agent

# Install dependencies
pip install -e .
# or with uv:
uv sync
```

## Usage

### REPL Mode

```bash
python -m zero_agent
# or
zero-agent
```

### Single Execution

```bash
zero-agent --once "list files in current directory"
```

### Start with Mode

```bash
zero-agent --mode yolo    # Auto-run safe operations
zero-agent --mode plan    # Read-only mode
zero-agent --mode ask     # Confirm based on config (default)
```

## Modes

| Mode | Description |
|------|-------------|
| **plan** | Read-only, all write operations denied |
| **ask** | Confirm based on config (default) |
| **yolo** | Auto-run safe operations, only confirm high-risk |

Press **Tab** to cycle modes.

## Languages

| Lang | Command | Description |
|------|---------|-------------|
| English | `/en` | Default |
| 中文 | `/zh` | Chinese |
| 日本語 | `/ja` | Japanese |

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

## Built-in Tools

| Tool | Description |
|------|-------------|
| `run_shell` | Execute shell commands (pure Python) |
| `search` | DuckDuckGo web search |

Supported commands: `ls`, `cat`, `head`, `tail`, `cp`, `mv`, `rm`, `mkdir`, `touch`, `find`, `grep`, `pwd`, `which`, `search`

## Configuration

Edit `config.yaml` or `~/.zero-agent/config.yaml`:

```yaml
llm:
  model: "gemma3:4b"
  base_url: "http://localhost:11434"

security:
  yolo_mode: false
  trust_current_dir: true
  permissions:
    run_shell: confirm

history:
  max_tokens: 8000
  compress_threshold: 0.8
```

## Project Structure

```
src/zero_agent/
├── agent.py            # Core agent (REPL)
├── cli.py              # CLI entry point
├── config.py           # Configuration
├── history.py          # History management with compression
├── prompts.py          # Dynamic system prompts
├── llm/                # LLM adapters
│   └── ollama.py       # Ollama adapter
├── fs/                 # Cross-platform file operations
│   └── operations.py   # Pure Python (no shell)
├── search/             # Web search
│   └── duckduckgo.py   # DuckDuckGo API
├── feedback/           # Hallucination prevention
│   └── verifier.py     # Tool result verification
├── security/           # Security layer
│   ├── command.py      # Command parser + risk detection
│   └── path_trust.py   # Path trust system
├── builtin/            # Built-in tools
│   └── shell.py        # Shell execution
├── mcp/                # MCP client
├── skills/             # Skills loader
└── memory/             # Memory management
```

## Hallucination Prevention

Small models may ignore error messages and assume success. Zero Agent uses:

1. **Structured Results**
   ```
   [TOOL RESULT: run_shell]
   STATUS: FAILURE ✗
   ERROR: Permission denied
   [ACTION REQUIRED: Acknowledge failure]
   [END RESULT]
   
   [IMPORTANT: The tool FAILED. Do NOT proceed as if it succeeded.]
   ```

2. **Explicit Status Markers** - `SUCCESS ✓` / `FAILURE ✗`

3. **System Prompt Instructions** - "Always check tool STATUS. FAILURE means do NOT proceed."

## Cross-Platform Design

All file operations use pure Python:
- `pathlib` for path handling
- `shutil` for file operations
- `os` for environment

No shell dependency - consistent behavior on Windows, Linux, macOS.

## Testing

```bash
pytest tests/ -v
```

## License

MIT

## Contributing

PRs welcome! Focus on:
- Small model optimization
- Cross-platform compatibility
- Security improvements