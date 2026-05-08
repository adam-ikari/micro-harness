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
    # Path trust settings
    trust_current_dir: bool = False
    ask_trust_on_startup: bool = True


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


# Two-tier config paths
USER_CONFIG_PATH = Path.home() / ".zero-agent" / "config.yaml"
PROJECT_CONFIG_PATH = Path.cwd() / ".zero-agent" / "config.yaml"


def _deep_merge(base: dict, override: dict) -> dict:
    """Deep merge two dictionaries."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _get_default_config() -> dict:
    """Get default config dictionary."""
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
            "trust_current_dir": False,
            "ask_trust_on_startup": True,
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


def _create_project_config() -> None:
    """Create project config file if not exists."""
    project_config = PROJECT_CONFIG_PATH

    if project_config.exists():
        return

    # Create directory
    project_config.parent.mkdir(parents=True, exist_ok=True)

    # Write minimal config
    content = """# Zero Agent Project Config
# Auto-generated - customize as needed

# Override LLM settings (uncomment to use)
# llm:
#   model: "llama3:8b"

# Project-specific settings
security:
  trust_current_dir: true
"""
    project_config.write_text(content)


def load_config(path: str | None = None) -> Config:
    """Load config file.

    Two-tier priority:
    1. User global: ~/.zero-agent/config.yaml
    2. Project: ./.zero-agent/config.yaml (auto-created if not exists)

    Project config overrides user global config.
    """
    default_config = _get_default_config()
    merged_config = default_config.copy()

    # Load user global config
    user_config_path = Path(os.path.expanduser(str(USER_CONFIG_PATH)))
    if user_config_path.exists():
        with open(user_config_path) as f:
            user_config = yaml.safe_load(f) or {}
        merged_config = _deep_merge(merged_config, user_config)

    # Auto-create and load project config
    _create_project_config()
    if PROJECT_CONFIG_PATH.exists():
        with open(PROJECT_CONFIG_PATH) as f:
            project_config = yaml.safe_load(f) or {}
        merged_config = _deep_merge(merged_config, project_config)

    # Override with specified path if provided
    if path:
        config_path = Path(os.path.expanduser(path))
        if config_path.exists():
            with open(config_path) as f:
                user_config = yaml.safe_load(f) or {}
            merged_config = _deep_merge(merged_config, user_config)

    # Build Config object
    llm_config = LLMConfig(**merged_config.get("llm", {}))

    security_data = merged_config.get("security", {})
    shell_config = security_data.get("shell", {})
    security_config = SecurityConfig(
        permissions=security_data.get("permissions", {"run_shell": "confirm"}),
        yolo_mode=security_data.get("yolo_mode", False),
        shell_timeout=shell_config.get("timeout", 30),
        blocked_commands=shell_config.get("blocked_commands", []),
        confirm_patterns=shell_config.get("confirm_patterns", []),
        trust_current_dir=security_data.get("trust_current_dir", False),
        ask_trust_on_startup=security_data.get("ask_trust_on_startup", True),
    )

    history_config = HistoryConfig(**merged_config.get("history", {}))

    return Config(
        llm=llm_config,
        mcp_servers=merged_config.get("mcp_servers", {}),
        skill_paths=merged_config.get("skill_paths", ["~/.zero-agent/skills"]),
        security=security_config,
        history=history_config,
    )