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
        overflow: hidden;
    }
    """

    mode = reactive("ask")
    lang = reactive("en")
    model = reactive("gemma3:4b")

    def render(self) -> str:
        """Render status bar - adapts to terminal width."""
        mode_display = {
            "plan": "plan",
            "ask": "ask",
            "yolo": "yolo",
        }
        lang_display = {
            "en": "EN",
            "zh": "ZH",
            "ja": "JA",
        }

        # Get terminal width
        width = self.size.width

        # Truncate model name if needed
        model = self.model
        if len(model) > 15:
            model = model[:12] + "..."

        # Build display based on width
        if width < 30:
            # Very narrow: just mode
            return f"[bold]{mode_display.get(self.mode, self.mode)}[/]"
        elif width < 50:
            # Narrow: mode + lang
            return f"[bold]{mode_display.get(self.mode, self.mode)}[/] | {lang_display.get(self.lang, self.lang)}"
        else:
            # Normal: mode + lang + model
            return f"[bold]{mode_display.get(self.mode, self.mode)}[/] | {lang_display.get(self.lang, self.lang)} | {model}"
