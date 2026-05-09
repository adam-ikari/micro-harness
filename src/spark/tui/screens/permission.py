# src/spark/tui/screens/permission.py
"""Permission screen - confirmation dialog for tool calls."""

from textual.screen import ModalScreen
from textual.widgets import Static, Button
from textual.containers import Vertical, Horizontal
from textual.reactive import reactive


class PermissionScreen(ModalScreen[bool]):
    """Permission confirmation dialog."""

    DEFAULT_CSS = """
    PermissionScreen {
        align: center middle;
    }
    PermissionScreen > Vertical {
        width: 60;
        background: $surface;
        border: thick $primary;
        padding: 1;
    }
    PermissionScreen .title {
        text-style: bold;
        color: $warning;
        margin-bottom: 1;
    }
    PermissionScreen .tool-info {
        margin: 1 0;
        padding: 1;
        background: $surface-darken-1;
    }
    PermissionScreen Button {
        margin: 0 1;
    }
    """

    def __init__(self, tool_name: str, args: dict, lang: str = "en", **kwargs):
        super().__init__(**kwargs)
        self.tool_name = tool_name
        self.args = args
        self.lang = lang

    def compose(self):
        # Title
        if self.lang == "zh":
            title = "⚠️ 权限确认"
            tool_label = "工具"
            args_label = "参数"
            allow_text = "允许"
            deny_text = "拒绝"
        elif self.lang == "ja":
            title = "⚠️ 権限確認"
            tool_label = "ツール"
            args_label = "引数"
            allow_text = "許可"
            deny_text = "拒否"
        else:
            title = "⚠️ Permission Required"
            tool_label = "Tool"
            args_label = "Arguments"
            allow_text = "Allow"
            deny_text = "Deny"

        yield Vertical(
            Static(title, classes="title"),
            Static(f"{tool_label}: [bold]{self.tool_name}[/]"),
            Static(f"{args_label}: {self.args}", classes="tool-info"),
            Horizontal(
                Button(allow_text, id="allow", variant="success"),
                Button(deny_text, id="deny", variant="error"),
            ),
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "allow":
            self.dismiss(True)
        else:
            self.dismiss(False)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(False)
        elif event.key == "y":
            self.dismiss(True)
        elif event.key == "n":
            self.dismiss(False)
