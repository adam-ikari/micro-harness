# src/spark/cli.py
"""CLI entry point for spark."""

import click

from spark import __version__
from spark.config import load_config


@click.command()
@click.version_option(version=__version__)
@click.option("--config", "-c", type=click.Path(exists=False), help="Config file path")
@click.option("--once", "-o", "prompt", help="Run once with prompt and exit")
@click.option("--mode", "-m", type=click.Choice(["plan", "ask", "yolo"]), default="ask", help="Mode: plan, ask, yolo")
@click.option("--lang", "-l", type=click.Choice(["en", "zh", "ja"]), default="en", help="Language: en, zh, ja")
@click.option("--tui", "-t", is_flag=True, help="Launch TUI interface")
@click.option("--trust", is_flag=True, help="Trust current directory on startup (skip question)")
@click.option("--memory", type=click.Path(exists=False), help="Memory file path (default: ./.spark/memory.md)")
def main(config: str | None, prompt: str | None, mode: str, lang: str, tui: bool, trust: bool, memory: str | None) -> None:
    """Spark - Minimal CLI agent with MCP, Skills, and security control.

    Modes:
      plan: Read-only, no writes allowed
      ask:  Confirm based on config (default)
      yolo: Auto-run, only confirm high-risk

    Languages:
      en: English
      zh: 中文
      ja: 日本語

    Interfaces:
      TUI:  --tui for terminal UI (default for REPL)
      CLI:  --once for single execution

    Security:
      --trust: Trust current directory on startup (skip question)

    Memory:
      --memory: Specify memory file path (default: ./.spark/memory.md)
    """
    cfg = load_config(config)

    # Override trust setting if --trust flag is set
    if trust:
        cfg.security.trust_current_dir = True
        cfg.security.ask_trust_on_startup = False

    # Set memory path
    memory_path = memory or "./.spark/memory.md"

    if prompt:
        # Single execution mode
        from spark.agent import Agent
        from spark.memory import MemoryManager
        from spark.llm import OllamaAdapter

        agent = Agent(cfg, mode=mode, lang=lang)

        # Initialize memory manager
        llm = OllamaAdapter(cfg.llm)
        memory_manager = MemoryManager(memory_path, llm)
        agent.history.set_memory_manager(memory_manager)

        print(agent.run_once(prompt))

        # Save to memory on exit
        agent.history.save_to_memory()

    elif tui:
        # TUI mode
        from spark.tui import ZeroAgentApp
        app = ZeroAgentApp(config=cfg, mode=mode, lang=lang)
        app.run()
    else:
        # Default REPL mode
        from spark.agent import Agent
        from spark.memory import MemoryManager
        from spark.llm import OllamaAdapter

        agent = Agent(cfg, mode=mode, lang=lang)

        # Initialize memory manager
        llm = OllamaAdapter(cfg.llm)
        memory_manager = MemoryManager(memory_path, llm)
        agent.history.set_memory_manager(memory_manager)

        agent.start_repl()

        # Save to memory on exit
        agent.history.save_to_memory()


if __name__ == "__main__":
    main()