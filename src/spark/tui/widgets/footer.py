# src/spark/tui/widgets/footer.py
"""Footer widget - keyboard shortcuts display."""

from textual.widget import Widget
from textual.reactive import reactive


class Footer(Widget):
    """Footer bar widget showing keyboard shortcuts."""

    DEFAULT_CSS = """
    Footer {
        dock: bottom;
        height: 1;
        background: $surface-darken-2;
        color: $text-muted;
        padding: 0 1;
        overflow: hidden;
    }
    """

    lang = reactive("en")

    def render(self) -> str:
        """Render footer - adapts to terminal width."""
        width = self.size.width

        if self.lang == "zh":
            if width < 40:
                return "[bold]Tab[/] 切换 | [bold]/help[/]"
            return "[bold]Tab[/] 切换模式 | [bold]/help[/] 帮助 | [bold]/exit[/] 退出"
        elif self.lang == "ja":
            if width < 40:
                return "[bold]Tab[/] 切替 | [bold]/help[/]"
            return "[bold]Tab[/] モード切替 | [bold]/help[/] ヘルプ | [bold]/exit[/] 終了"
        else:
            if width < 40:
                return "[bold]Tab[/] Mode | [bold]/help[/]"
            return "[bold]Tab[/] Cycle mode | [bold]/help[/] Help | [bold]/exit[/] Exit"
