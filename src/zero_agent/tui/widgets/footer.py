# src/zero_agent/tui/widgets/footer.py
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
    }
    """

    lang = reactive("en")

    def render(self) -> str:
        if self.lang == "zh":
            return "[bold]Tab[/] 切换模式 │ [bold]/help[/] 帮助 │ [bold]/exit[/] 退出"
        elif self.lang == "ja":
            return "[bold]Tab[/] モード切替 │ [bold]/help[/] ヘルプ │ [bold]/exit[/] 終了"
        else:
            return "[bold]Tab[/] Cycle mode │ [bold]/help[/] Help │ [bold]/exit[/] Exit"
