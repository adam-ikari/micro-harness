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
@click.option("--trust", is_flag=True, help="Trust current directory on startup (skip question)")
@click.option("--memory", type=click.Path(exists=False), help="Memory file path (default: ./.spark/memory.md)")
@click.option("--model", help="Model name (e.g., gemma3:4b, gpt-4)")
@click.option("--base-api-url", help="API base URL (e.g., http://localhost:11434)")
def main(config: str | None, prompt: str | None, mode: str, lang: str, trust: bool, memory: str | None, model: str | None, base_api_url: str | None) -> None:
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
      TUI:  Default interface
      CLI:  --once for single execution

    Security:
      --trust: Trust current directory on startup (skip question)

    Memory:
      --memory: Specify memory file path (default: ./.spark/memory.md)

    LLM:
      --model: Model name (e.g., gemma3:4b, gpt-4)
      --base-api-url: API base URL (e.g., http://localhost:11434)
    """
    cfg = load_config(config)

    # Override LLM settings
    if model:
        cfg.llm.model = model
    if base_api_url:
        cfg.llm.base_url = base_api_url

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
        from spark.errors import LLMError

        try:
            agent = Agent(cfg, mode=mode, lang=lang)

            # Initialize memory manager
            llm = OllamaAdapter(cfg.llm)
            memory_manager = MemoryManager(memory_path, llm)
            agent.history.set_memory_manager(memory_manager)

            print(agent.run_once(prompt))

            # Save to memory on exit
            agent.history.save_to_memory()
        except LLMError as e:
            print(f"LLM Error: {e}")
            return 1
        except Exception as e:
            print(f"Error: {e}")
            return 1

    else:
        # Default TUI mode
        from spark.tui import ZeroAgentApp
        app = ZeroAgentApp(config=cfg, mode=mode, lang=lang)
        app.run()


if __name__ == "__main__":
    main()