# src/spark/tui/widgets/message_item.py
"""Message item widgets - individual message display."""

from textual.widget import Widget
from textual.reactive import reactive


class UserMessage(Widget):
    """User message widget - adapts to terminal width."""

    DEFAULT_CSS = """
    UserMessage {
        margin: 1 0;
        padding: 1;
        background: $primary-darken-2;
        border-left: thick $primary;
        overflow: hidden;
    }
    """

    content = reactive("")

    def __init__(self, content: str, **kwargs):
        super().__init__(**kwargs)
        self.content = content

    def render(self) -> str:
        width = self.size.width
        # Truncate content if too long for narrow terminals
        content = self.content
        if width > 0 and len(content) > width * 3:
            content = content[:width * 3 - 10] + "..."
        return f"[bold blue]You:[/] {content}"

    def update_content(self, content: str):
        self.content = content


class AssistantMessage(Widget):
    """Assistant message widget - adapts to terminal width."""

    DEFAULT_CSS = """
    AssistantMessage {
        margin: 1 0;
        padding: 1;
        background: $surface-darken-1;
        border-left: thick $secondary;
        overflow: hidden;
    }
    """

    content = reactive("")

    def __init__(self, content: str, **kwargs):
        super().__init__(**kwargs)
        self.content = content

    def render(self) -> str:
        width = self.size.width
        display = self.content if self.content else "..."
        # Truncate content if too long for narrow terminals
        if width > 0 and len(display) > width * 5:
            display = display[:width * 5 - 10] + "..."
        return f"[bold green]Assistant:[/] {display}"

    def update_content(self, content: str):
        self.content = content


class ToolMessage(Widget):
    """Tool call message widget - adapts to terminal width."""

    DEFAULT_CSS = """
    ToolMessage {
        margin: 1 0;
        padding: 1;
        background: $surface-darken-2;
        overflow: hidden;
    }
    ToolMessage.pending { border-left: thick $warning; }
    ToolMessage.running { border-left: thick $primary; }
    ToolMessage.success { border-left: thick $success; }
    ToolMessage.error { border-left: thick $error; }
    ToolMessage.denied { border-left: thick $error; }
    """

    tool_name = reactive("")
    status = reactive("pending")
    result = reactive("")

    def __init__(self, tool_name: str, args: dict, status: str, **kwargs):
        super().__init__(**kwargs)
        self.tool_name = tool_name
        self.args = args
        self.status = status
        self.result = ""

    def render(self) -> str:
        width = self.size.width
        status_icon = {
            "pending": "...",
            "running": "...",
            "success": "OK",
            "error": "ERR",
            "denied": "DENY",
        }
        icon = status_icon.get(self.status, "?")

        # Show tool call - adapt to width
        if self.tool_name == "Bash":
            cmd = self.args.get("command", "")
            # Truncate command for narrow terminals
            if width > 0 and len(cmd) > width - 15:
                cmd = cmd[:width - 18] + "..."
            display = f"[bold yellow]{icon}[/] {self.tool_name}: [dim]$ {cmd}[/]"
        else:
            display = f"[bold yellow]{icon}[/] {self.tool_name}"

        # Show result - adapt to width
        if self.result:
            result_text = self.result
            max_len = max(50, width - 10) if width > 0 else 100
            if len(result_text) > max_len:
                result_text = result_text[:max_len - 3] + "..."
            display += f"\n  {result_text}"

        return display

    def update_status(self, status: str, result: str = ""):
        self.status = status
        if result:
            self.result = result
        self.refresh()
