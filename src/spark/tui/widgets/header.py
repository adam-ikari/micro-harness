# src/spark/tui/widgets/header.py
"""Header widget - status bar showing mode, language, and model."""

from textual.widget import Widget
from textual.reactive import reactive


class Header(Widget):
    """Status bar widget showing mode, language, and model info."""

    DEFAULT_CSS = """
    Header {
        dock: top;
        height: 1;
        background: $primary;
        color: $text;
        padding: 0 1;
    }
    """

    mode = reactive("ask")
    lang = reactive("en")
    model = reactive("gemma3:4b")

    def render(self) -> str:
        """Render status bar."""
        mode_display = {
            "plan": "📋 plan",
            "ask": "❓ ask",
            "yolo": "🚀 yolo",
        }
        lang_display = {
            "en": "EN",
            "zh": "中",
            "ja": "日",
        }
        return f"[bold]{mode_display.get(self.mode, self.mode)}[/] │ {lang_display.get(self.lang, self.lang)} │ {self.model}"
