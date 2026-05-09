# src/spark/tui/app.py
"""Main TUI application for spark."""

import asyncio
from typing import Any

from textual.app import App
from textual.binding import Binding
from textual.reactive import reactive

from spark.config import Config, load_config
from spark.llm import OllamaAdapter
from spark.history import HistoryManager
from spark.mcp.client import MCPClient
from spark.skills.loader import SkillLoader
from spark.security import SecurityManager, Decision, PathTrustManager, PathParser, CommandParser
from spark.builtin.shell import execute as shell_execute, get_tool_definition

from spark.tui.widgets import Header, MessageList, InputBox, Footer
from spark.tui.screens import PermissionScreen, TrustDialog
from textual.widgets import Input


# Multi-language text
I18N = {
    "en": {
        "welcome": "Welcome to Spark! Type your message or /help for commands.",
        "cleared": "History cleared.",
        "mode_changed": "Mode: {}",
        "lang_changed": "Language: {}",
        "error_denied": "Error: Tool '{}' denied.",
        "error_cancelled": "Cancelled.",
        "error_write_plan": "Write operations not allowed in plan mode.",
        "switch_to_ask": "Switch to ask mode? [y/N]: ",
        "switched_mode": "Switched to {} mode.",
    },
    "zh": {
        "welcome": "欢迎使用 Spark！输入消息或 /help 查看命令。",
        "cleared": "历史已清空。",
        "mode_changed": "模式: {}",
        "lang_changed": "语言: {}",
        "error_denied": "错误: 工具 '{}' 被拒绝。",
        "error_cancelled": "已取消。",
        "error_write_plan": "Plan 模式不允许写入操作。",
        "switch_to_ask": "切换到 ask 模式? [y/N]: ",
        "switched_mode": "已切换到 {} 模式。",
    },
    "ja": {
        "welcome": "Spark へようこそ！メッセージを入力するか /help でコマンドを確認。",
        "cleared": "履歴をクリアしました。",
        "mode_changed": "モード: {}",
        "lang_changed": "言語: {}",
        "error_denied": "エラー: ツール '{}' は拒否されました。",
        "error_cancelled": "キャンセルしました。",
        "error_write_plan": "Plan モードでは書き込みできません。",
        "switch_to_ask": "ask モードに切替? [y/N]: ",
        "switched_mode": "{} モードに切替しました。",
    },
}

# Mode definitions
MODES = ["plan", "ask", "yolo"]
LANGUAGES = ["en", "zh", "ja"]


class ZeroAgentApp(App):
    """Spark TUI application."""

    CSS_PATH = "styles/app.css"

    BINDINGS = [
        Binding("tab", "cycle_mode", "Mode"),
        Binding("ctrl+l", "clear_screen", "Clear"),
        Binding("ctrl+c", "quit", "Quit"),
    ]

    mode = reactive("ask")
    lang = reactive("en")
    model = reactive("gemma3:4b")

    def __init__(self, config: Config = None, mode: str = "ask", lang: str = "en"):
        super().__init__()
        self.config = config or load_config()
        self.mode = mode if mode in MODES else "ask"
        self.lang = lang if lang in LANGUAGES else "en"

        # Core components
        self.llm = OllamaAdapter(self.config.llm)
        self.history = HistoryManager(self.config.history)
        self.skills = SkillLoader(self.config.skill_paths)
        self.security = SecurityManager(self.config.security, yolo=False)
        self.mcp_client = MCPClient(self.config.mcp_servers)

        # Path trust system
        self.path_trust = PathTrustManager(trust_current_dir=config.security.trust_current_dir)
        self.path_parser = PathParser(self.llm)

        # Command parser for security
        self.cmd_parser = CommandParser()

        self.skills.load_all()
        self.model = self.config.llm.model

        # UI component references
        self._message_list: MessageList = None
        self._input_box: InputBox = None
        self._processing = False

    def compose(self):
        yield Header()
        yield MessageList()
        yield InputBox()
        yield Footer()

    def on_mount(self) -> None:
        """Initialize after mount."""
        self._message_list = self.query_one(MessageList)
        self._input_box = self.query_one(InputBox)

        # Show welcome message
        welcome = I18N[self.lang]["welcome"]
        self._message_list.add_assistant_message(welcome)

        # Ask about trusting current directory
        if self.config.security.ask_trust_on_startup and not self.config.security.trust_current_dir:
            self._show_trust_dialog()

        self._input_box.focus()

    def _show_trust_dialog(self) -> None:
        """Show trust dialog for current directory."""
        def on_trust_result(trusted: bool) -> None:
            if trusted:
                self.path_trust.add_trusted_path(self.path_trust.current_dir)
                self._message_list.add_assistant_message(
                    f"Trusted directory: {self.path_trust.current_dir}"
                )

        self.push_screen(TrustDialog(lang=self.lang), on_trust_result)

    def t(self, key: str, *args) -> str:
        """Get text for current language."""
        text = I18N.get(self.lang, I18N["en"]).get(key, key)
        if args:
            return text.format(*args)
        return text

    def action_cycle_mode(self) -> None:
        """Cycle through modes."""
        idx = MODES.index(self.mode)
        self.mode = MODES[(idx + 1) % len(MODES)]
        self.security.yolo = (self.mode == "yolo")
        self._message_list.add_assistant_message(self.t("mode_changed", self.mode))

    def action_clear_screen(self) -> None:
        """Clear screen."""
        self._message_list.clear()
        self.history.clear()
        self._message_list.add_assistant_message(self.t("cleared"))

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submission."""
        if self._processing:
            return

        user_input = event.value.strip()
        if not user_input:
            return

        self._input_box.clear()

        # Handle commands
        if user_input.startswith("/"):
            self._handle_command(user_input)
            return

        # Handle regular messages
        self._process_message(user_input)

    def _handle_command(self, cmd: str) -> None:
        """Handle slash commands."""
        cmd = cmd.lower()

        if cmd == "/exit":
            self.exit()
        elif cmd == "/clear":
            self.action_clear_screen()
        elif cmd == "/help":
            self._show_help()
        elif cmd in ("/plan", "/ask", "/yolo"):
            self.mode = cmd[1:]
            self.security.yolo = (self.mode == "yolo")
            self._message_list.add_assistant_message(self.t("mode_changed", self.mode))
        elif cmd in ("/en", "/zh", "/ja"):
            self.lang = cmd[1:]
            self._message_list.add_assistant_message(self.t("lang_changed", self.lang))
        elif cmd == "/mode":
            self._message_list.add_assistant_message(f"Current mode: {self.mode}")
        elif cmd == "/lang":
            self._message_list.add_assistant_message(f"Current language: {self.lang}")
        else:
            self._message_list.add_assistant_message(f"Unknown command: {cmd}")

    def _show_help(self) -> None:
        """Show help."""
        if self.lang == "zh":
            help_text = """命令列表:
  /exit - 退出
  /clear - 清空历史
  /help - 显示帮助
  /mode - 显示当前模式
  /lang - 显示当前语言
  /plan, /ask, /yolo - 切换模式
  /en, /zh, /ja - 切换语言

快捷键:
  Tab - 切换模式
  Ctrl+L - 清空屏幕"""
        elif self.lang == "ja":
            help_text = """コマンド一覧:
  /exit - 終了
  /clear - 履歴クリア
  /help - ヘルプ表示
  /mode - 現在のモード
  /lang - 現在の言語
  /plan, /ask, /yolo - モード切替
  /en, /zh, /ja - 言語切替

ショートカット:
  Tab - モード切替
  Ctrl+L - 画面クリア"""
        else:
            help_text = """Commands:
  /exit - Exit
  /clear - Clear history
  /help - Show help
  /mode - Show current mode
  /lang - Show current language
  /plan, /ask, /yolo - Switch mode
  /en, /zh, /ja - Switch language

Shortcuts:
  Tab - Cycle mode
  Ctrl+L - Clear screen"""

        self._message_list.add_assistant_message(help_text)

    def _process_message(self, user_input: str) -> None:
        """Process user message."""
        self._processing = True

        # Show user message
        self._message_list.add_user_message(user_input)

        # Build messages
        messages = self._build_messages(user_input)

        # Call LLM
        try:
            response = self.llm.chat(messages, self._get_all_tools())
            result = self._process_response(response)
            self._message_list.add_assistant_message(result)
            self.history.add("user", user_input)
            self.history.add("assistant", result)
        except Exception as e:
            self._message_list.add_assistant_message(f"Error: {e}")
        finally:
            self._processing = False

    def _build_messages(self, user_input: str) -> list[dict]:
        """Build message list."""
        messages = [{"role": "system", "content": "You are a helpful AI assistant."}]

        skills_prompt = self.skills.get_all_skills_prompt()
        if skills_prompt:
            messages.append({"role": "system", "content": f"Skills:\n{skills_prompt}"})

        messages.extend(self.history.get_messages())
        messages.append({"role": "user", "content": user_input})
        return messages

    def _get_all_tools(self) -> list[dict]:
        """Get all tools."""
        return [get_tool_definition()]

    def _process_response(self, response) -> str:
        """Process LLM response."""
        if response.tool_calls:
            results = []
            for call in response.tool_calls:
                tool_name = call.get("function", {}).get("name", "")
                args = call.get("function", {}).get("arguments", {})
                result = self._handle_tool_call(tool_name, args)
                results.append(f"[{tool_name}]: {result}")
            return "\n".join(results)
        return response.content

    def _handle_tool_call(self, tool_name: str, args: dict) -> str:
        """Handle tool call."""
        # Path trust check for shell commands
        if tool_name == "Bash":
            command = args.get("command", "")
            paths = self.path_parser.parse(command)

            # Check each path
            for path, operation in paths:
                decision = self.path_trust.check_path_permission(path, operation, self.mode)
                if decision == Decision.DENY:
                    if self.mode == "plan" and operation == "write":
                        return self.t("error_write_plan")
                    return f"Error: Path '{path}' not trusted for {operation}."

                if decision == Decision.CONFIRM:
                    # For TUI, we'll add to trusted and continue
                    self.path_trust.add_trusted_path(path)

        # Security check
        decision = self._get_tool_decision(tool_name, args)

        if decision == Decision.DENY:
            if self.mode == "plan" and self._is_write_command(args.get("command", "")):
                return self.t("error_write_plan")
            return self.t("error_denied", tool_name)

        if decision == Decision.CONFIRM:
            # Show permission confirmation dialog
            confirmed = self._show_permission_dialog(tool_name, args)
            if not confirmed:
                return self.t("error_cancelled")

        if tool_name == "Bash":
            result = shell_execute(args.get("command", ""))
            return result["stdout"] if result["success"] else f"Error: {result['error']}"

        return f"Error: Unknown tool '{tool_name}'"

    def _get_tool_decision(self, tool_name: str, args: dict) -> Decision:
        """Get tool call decision."""
        if self.mode == "yolo":
            self.security.yolo = True
            return self.security.check(tool_name, args)
        elif self.mode == "plan":
            command = args.get("command", "")
            if self.security.risk_detector.is_blocked(command):
                return Decision.DENY
            if self._is_write_command(command):
                return Decision.DENY
            return Decision.CONFIRM
        else:
            self.security.yolo = False
            return self.security.check(tool_name, args)

    def _is_write_command(self, command: str) -> bool:
        """Check if command is a write operation using CommandParser."""
        return self.cmd_parser.is_write_operation(command)

    def _show_permission_dialog(self, tool_name: str, args: dict) -> bool:
        """Show permission confirmation dialog (sync version)."""
        # Use push_screen with callback for async compatibility
        result = False

        def on_result(confirmed: bool) -> None:
            nonlocal result
            result = confirmed

        self.push_screen(PermissionScreen(tool_name, args, self.lang), on_result)
        return result
