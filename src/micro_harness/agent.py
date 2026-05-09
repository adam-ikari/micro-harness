# src/micro_harness/agent.py
"""Agent core for zero-agent."""

from typing import Any

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings

from micro_harness.config import Config
from micro_harness.history import HistoryManager
from micro_harness.llm import OllamaAdapter
from micro_harness.mcp.client import MCPClient
from micro_harness.skills.loader import SkillLoader
from micro_harness.security import SecurityManager, Decision, PathTrustManager, PathParser, CommandParser
from micro_harness.builtin.shell import execute as shell_execute, get_tool_definition
from micro_harness.prompts import get_system_prompt, build_context_aware_prompt, detect_context
from micro_harness.feedback import HallucinationPreventer, ResultStatus


# Language definitions
LANGUAGES = ["en", "zh", "ja"]

# Multi-language text
I18N = {
    "en": {
        "welcome": "Zero Agent. Tab=mode, Ctrl+T=lang, /exit to quit, /help for commands.",
        "mode_switch": "Mode: {}",
        "cleared": "Cleared.",
        "help": """Commands: /exit, /clear, /help, /mode, /lang
Mode commands: /plan, /ask, /yolo
Lang commands: /en, /zh, /ja
Modes:
  plan: Read-only, no writes allowed
  ask:  Confirm based on config (default)
  yolo: Auto-run, only confirm high-risk
Shortcut: Tab to cycle modes""",
        "current_mode": "Current mode: {}",
        "modes_info": "Modes: plan -> ask -> yolo -> plan",
        "current_lang": "Current language: {}",
        "langs_info": "Languages: en -> zh -> ja -> en",
        "allow": "Allow: {}({})? [y/N]: ",
        "write_blocked": "Write operation blocked in plan mode. Switch to ask mode? [y/N]: ",
        "switched_mode": "Switched to {} mode.",
        "error_denied": "Error: Tool call '{}' is denied.",
        "error_cancelled": "Error: Cancelled.",
        "error_write_plan": "Error: Write operations not allowed in plan mode.",
        "error_unknown": "Error: Unknown tool '{}'",
        "exit_hint": "\n/exit to quit.",
    },
    "zh": {
        "welcome": "Zero Agent. Tab=模式, Ctrl+T=语言, /exit 退出, /help 帮助。",
        "mode_switch": "模式: {}",
        "cleared": "已清空。",
        "help": """命令: /exit, /clear, /help, /mode, /lang
模式命令: /plan, /ask, /yolo
语言命令: /en, /zh, /ja
模式:
  plan: 只读模式，禁止写入
  ask:  按配置确认（默认）
  yolo: 自动执行，仅高风险确认
快捷键:
  Tab:    切换模式
  Ctrl+T: 切换语言""",
        "current_mode": "当前模式: {}",
        "modes_info": "模式: plan -> ask -> yolo -> plan",
        "current_lang": "当前语言: {}",
        "langs_info": "语言: en -> zh -> ja -> en",
        "allow": "允许: {}({})? [y/N]: ",
        "write_blocked": "Plan 模式禁止写入。切换到 ask 模式? [y/N]: ",
        "switched_mode": "已切换到 {} 模式。",
        "error_denied": "错误: 工具 '{}' 被拒绝。",
        "error_cancelled": "错误: 已取消。",
        "error_write_plan": "错误: Plan 模式不允许写入操作。",
        "error_unknown": "错误: 未知工具 '{}'",
        "exit_hint": "\n/exit 退出。",
    },
    "ja": {
        "welcome": "Zero Agent. Tab でモード切替, /exit で終了, /help でヘルプ。",
        "mode_switch": "モード: {}",
        "cleared": "クリアしました。",
        "help": """コマンド: /exit, /clear, /help, /mode, /lang
モード:
  plan: 読み取り専用、書き込み禁止
  ask:  設定に基づき確認（デフォルト）
  yolo: 自動実行、高リスクのみ確認
Tab でモード切替。""",
        "current_mode": "現在のモード: {}",
        "modes_info": "モード: plan -> ask -> yolo -> plan",
        "current_lang": "現在の言語: {}",
        "langs_info": "言語: en -> zh -> ja -> en",
        "allow": "許可: {}({})? [y/N]: ",
        "write_blocked": "Plan モードでは書き込み禁止。ask モードに切替? [y/N]: ",
        "switched_mode": "{} モードに切替しました。",
        "error_denied": "エラー: ツール '{}' は拒否されました。",
        "error_cancelled": "エラー: キャンセルしました。",
        "error_write_plan": "エラー: Plan モードでは書き込みできません。",
        "error_unknown": "エラー: 不明なツール '{}'",
        "exit_hint": "\n/exit で終了。",
    },
}


# Mode definitions
MODES = ["plan", "ask", "yolo"]
MODE_PROMPTS = {
    "plan": "[plan] ",
    "ask": "[ask] ",
    "yolo": "[yolo] ",
}


class Agent:
    """Zero Agent core."""

    def __init__(self, config: Config, mode: str = "ask", lang: str = "en"):
        self.config = config
        self.llm = OllamaAdapter(config.llm)
        self.history = HistoryManager(config.history)
        self.skills = SkillLoader(config.skill_paths)
        self.security = SecurityManager(config.security, yolo=False)
        self.mcp_client = MCPClient(config.mcp_servers)
        self.mcp_client.connect_all_async()  # Non-blocking async connection
        self.mode = mode if mode in MODES else "ask"
        self.lang = lang if lang in LANGUAGES else "en"

        # Path trust system
        self.path_trust = PathTrustManager(trust_current_dir=config.security.trust_current_dir)
        self.path_parser = PathParser(self.llm)

        # Command parser for security
        self.cmd_parser = CommandParser()

        # Hallucination preventer for small models
        self.hallucination_preventer = HallucinationPreventer()

        # Track last tool result for verification
        self._last_verified_result = None

        # Ask about trusting current dir on startup
        if config.security.ask_trust_on_startup and not config.security.trust_current_dir:
            self.path_trust.ask_trust_current_dir()

    def t(self, key: str, *args) -> str:
        """Get text for current language."""
        text = I18N.get(self.lang, I18N["en"]).get(key, key)
        if args:
            return text.format(*args)
        return text

    def _build_messages(self, user_input: str) -> list[dict]:
        """Build messages for LLM with optimized prompts."""
        # Use context-aware system prompt
        system_prompt = build_context_aware_prompt(self.mode, user_input)
        messages = [{"role": "system", "content": system_prompt}]

        # Only load relevant skills (optimization for small models)
        skills_prompt = self._get_relevant_skills_prompt(user_input)
        if skills_prompt:
            messages.append({"role": "system", "content": f"Skills:\n{skills_prompt}"})

        messages.extend(self.history.get_messages())
        messages.append({"role": "user", "content": user_input})
        return messages

    def _get_relevant_skills_prompt(self, user_input: str) -> str:
        """Get only relevant skills based on user input.

        Optimization: Don't load all skills, only matching ones.
        """
        # Get skills with triggers
        skills_with_triggers = self.skills.get_skills_with_triggers()

        if not skills_with_triggers:
            # Fallback to all skills if no triggers defined
            return self.skills.get_all_skills_prompt()

        # Match skills by keywords
        matched = []
        user_lower = user_input.lower()

        for skill in skills_with_triggers:
            trigger = skill.get("trigger", {})
            keywords = trigger.get("keywords", [])

            # Check if any keyword matches
            for kw in keywords:
                if kw.lower() in user_lower:
                    matched.append(skill)
                    break

        # Limit to top 2 skills to save tokens
        if matched:
            return "\n".join(
                f"## {s['name']}\n{s['content'][:500]}"
                for s in matched[:2]
            )

        # No match, return empty (saves tokens)
        return ""

    def _get_all_tools(self) -> list[dict]:
        """Get all available tools."""
        tools = [get_tool_definition()]

        # Check MCP connection status (polling)
        if self.mcp_client.is_connecting():
            # Connection in progress, wait briefly
            import time
            time.sleep(0.1)  # Brief wait for connection

        if self.mcp_client.has_tools():
            tools.extend(self.mcp_client.get_tool_definitions())
        return tools

    def _handle_tool_call(self, tool_name: str, args: dict) -> str:
        """Handle tool call."""
        # Path trust check for shell commands
        if tool_name == "run_shell":
            command = args.get("command", "")
            paths = self.path_parser.parse(command)

            # Check each path
            for path, operation in paths:
                decision = self.path_trust.check_path_permission(path, operation, self.mode)
                if decision == Decision.DENY:
                    if self.mode == "plan" and operation == "write":
                        switch = input(self.t("write_blocked"))
                        if switch.lower() == "y":
                            self.mode = "ask"
                            print(self.t("switched_mode", self.mode))
                        else:
                            return self.hallucination_preventer.format_denied(tool_name, self.t("error_write_plan"))
                    else:
                        return self.hallucination_preventer.format_denied(tool_name, f"Path '{path}' not trusted for {operation}.")

                if decision == Decision.CONFIRM:
                    confirm = input(f"Path {path} not trusted. Allow {operation}? [y/N]: ")
                    if confirm.lower() != "y":
                        return self.hallucination_preventer.format_denied(tool_name, self.t("error_cancelled"))
                    # Add to trusted for this session
                    self.path_trust.add_trusted_path(path)

        # Original security check
        decision = self._get_tool_decision(tool_name, args)

        if decision == Decision.DENY:
            # Plan 模式下写入命令被拒绝时，询问是否切换模式
            if self.mode == "plan" and self._is_write_command(args.get("command", "")):
                switch = input(self.t("write_blocked"))
                if switch.lower() == "y":
                    self.mode = "ask"
                    print(self.t("switched_mode", self.mode))
                    decision = self._get_tool_decision(tool_name, args)
                else:
                    return self.hallucination_preventer.format_denied(tool_name, self.t("error_write_plan"))
            else:
                return self.hallucination_preventer.format_denied(tool_name, self.t("error_denied", tool_name))

        if decision == Decision.CONFIRM:
            confirm = input(self.t("allow", tool_name, args))
            if confirm.lower() != "y":
                return self.hallucination_preventer.format_denied(tool_name, self.t("error_cancelled"))

        if tool_name == "run_shell":
            result = shell_execute(args.get("command", ""))
            # Use hallucination preventer for structured feedback
            formatted = self.hallucination_preventer.format_result(tool_name, result)
            # Store for response verification
            self._last_verified_result = self.hallucination_preventer.verifier.verify(tool_name, result)
            return formatted
        return self.hallucination_preventer.format_error(tool_name, self.t("error_unknown", tool_name))

    def _get_tool_decision(self, tool_name: str, args: dict) -> Decision:
        """Get tool call decision based on current mode."""
        if self.mode == "yolo":
            # YOLO 模式：只对高风险确认
            self.security.yolo = True
            return self.security.check(tool_name, args)
        elif self.mode == "plan":
            # Plan 模式：禁止写入操作
            command = args.get("command", "")
            if self.security.risk_detector.is_blocked(command):
                return Decision.DENY
            if self._is_write_command(command):
                return Decision.DENY
            # Read-only operations also need confirmation
            return Decision.CONFIRM
        else:
            # Ask 模式：按配置检查
            self.security.yolo = False
            return self.security.check(tool_name, args)

    def _is_write_command(self, command: str) -> bool:
        """Check if command is a write operation using CommandParser."""
        return self.cmd_parser.is_write_operation(command)

    def _cycle_mode(self) -> None:
        """Cycle modes: plan -> ask -> yolo -> plan"""
        idx = MODES.index(self.mode)
        self.mode = MODES[(idx + 1) % len(MODES)]
        self.security.yolo = (self.mode == "yolo")

    def _cycle_lang(self) -> None:
        """Cycle languages: en -> zh -> ja -> en"""
        idx = LANGUAGES.index(self.lang)
        self.lang = LANGUAGES[(idx + 1) % len(LANGUAGES)]

    def _process_response(self, response) -> str:
        """Process LLM response."""
        if response.tool_calls:
            results = []
            for call in response.tool_calls:
                tool_name = call.get("function", {}).get("name", "")
                args = call.get("function", {}).get("arguments", {})
                result = self._handle_tool_call(tool_name, args)
                results.append(result)
            return "\n\n".join(results)
        return response.content

    def _verify_model_acknowledgment(self, model_response: str) -> str:
        """Verify model acknowledged tool results correctly.

        Small models may ignore failure messages and hallucinate success.
        This adds a reminder if the model didn't acknowledge a failure.
        """
        if self._last_verified_result is None:
            return model_response

        acknowledged, hint = self.hallucination_preventer.check_model_response(
            model_response, self._last_verified_result
        )

        if not acknowledged:
            return f"{hint}\n\n{model_response}"

        return model_response

    def run_once(self, prompt: str) -> str:
        """Single execution mode."""
        messages = self._build_messages(prompt)
        response = self.llm.chat(messages, self._get_all_tools())
        result = self._process_response(response)
        self.history.add("user", prompt)
        self.history.add("assistant", result)
        return result

    def start_repl(self) -> None:
        """Start REPL interactive mode."""
        print(self.t("welcome"))

        kb = KeyBindings()

        @kb.add('tab')
        def _(event):
            """Tab key to cycle mode"""
            self._cycle_mode()
            event.app.current_buffer.text = ""
            print(self.t("mode_switch", self.mode))

        session = PromptSession(
            history=FileHistory(".micro_harness_history"),
            key_bindings=kb,
        )

        while True:
            try:
                prompt_text = MODE_PROMPTS.get(self.mode, ">>> ")
                user_input = session.prompt(prompt_text).strip()
                if not user_input:
                    continue

                if user_input == "/exit":
                    break
                if user_input == "/clear":
                    self.history.clear()
                    print(self.t("cleared"))
                    continue
                if user_input == "/help":
                    print(self.t("help"))
                    continue
                if user_input == "/mode":
                    print(self.t("current_mode", self.mode))
                    print(self.t("modes_info"))
                    continue
                if user_input == "/lang":
                    print(self.t("current_lang", self.lang))
                    print(self.t("langs_info"))
                    continue

                # Language switch commands
                if user_input in ("/en", "/zh", "/ja"):
                    self.lang = user_input[1:]
                    print(self.t("current_lang", self.lang))
                    continue

                # Mode switch commands
                if user_input in ("/plan", "/ask", "/yolo"):
                    self.mode = user_input[1:]
                    self.security.yolo = (self.mode == "yolo")
                    print(self.t("current_mode", self.mode))
                    continue

                response = self.llm.chat(self._build_messages(user_input), self._get_all_tools())
                result = self._process_response(response)
                self.history.add("user", user_input)
                self.history.add("assistant", result)

                if self.history.should_compress():
                    self.history.compress(self.llm)

                print(result)

            except KeyboardInterrupt:
                print(self.t("exit_hint"))
            except EOFError:
                break
