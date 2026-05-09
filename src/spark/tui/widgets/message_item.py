# src/spark/tui/widgets/message_item.py
"""Message item widgets - individual message display."""

from textual.widget import Widget
from textual.reactive import reactive


class UserMessage(Widget):
    """User message widget."""

    DEFAULT_CSS = """
    UserMessage {
        margin: 1 0;
        padding: 1;
        background: $primary-darken-2;
        border-left: thick $primary;
    }
    """

    content = reactive("")

    def __init__(self, content: str, **kwargs):
        super().__init__(**kwargs)
        self.content = content

    def render(self) -> str:
        return f"[bold blue]You:[/] {self.content}"

    def update_content(self, content: str):
        self.content = content


class AssistantMessage(Widget):
    """Assistant message widget."""

    DEFAULT_CSS = """
    AssistantMessage {
        margin: 1 0;
        padding: 1;
        background: $surface-darken-1;
        border-left: thick $secondary;
    }
    """

    content = reactive("")

    def __init__(self, content: str, **kwargs):
        super().__init__(**kwargs)
        self.content = content

    def render(self) -> str:
        display = self.content if self.content else "..."
        return f"[bold green]Assistant:[/] {display}"

    def update_content(self, content: str):
        self.content = content


class ToolMessage(Widget):
    """Tool call message widget."""

    DEFAULT_CSS = """
    ToolMessage {
        margin: 1 0;
        padding: 1;
        background: $surface-darken-2;
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
        status_icon = {
            "pending": "⏳",
            "running": "🔄",
            "success": "✅",
            "error": "❌",
            "denied": "🚫",
        }
        icon = status_icon.get(self.status, "❓")

        # Show tool call
        if self.tool_name == "run_shell":
            cmd = self.args.get("command", "")
            display = f"[bold yellow]{icon} Tool:[/] {self.tool_name}\n  [dim]$ {cmd}[/]"
        else:
            display = f"[bold yellow]{icon} Tool:[/] {self.tool_name}"

        # Show result
        if self.result:
            display += f"\n  [dim]{self.result[:200]}[/]"

        return display

    def update_status(self, status: str, result: str = ""):
        self.status = status
        if result:
            self.result = result
        self.refresh()
