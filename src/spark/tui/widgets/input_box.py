# src/spark/tui/widgets/input_box.py
"""Input box widget - user input area."""

from textual.widget import Widget
from textual.widgets import Input
from textual.containers import Horizontal
from textual.reactive import reactive


class InputBox(Horizontal):
    """Input box widget - adapts to terminal size."""

    DEFAULT_CSS = """
    InputBox {
        dock: bottom;
        height: 3;
        background: $surface-darken-1;
        border-top: solid $primary;
        padding: 0 1;
    }
    InputBox Input {
        height: 1fr;
        width: 1fr;
    }
    .mode-indicator {
        color: $accent;
        text-style: bold;
        min-width: 8;
    }
    """

    mode = reactive("ask")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._input = Input(placeholder="Type your message...")

    def compose(self):
        yield self._input

    def on_mount(self):
        self._input.focus()

    def get_value(self) -> str:
        return self._input.value

    def clear(self):
        self._input.value = ""

    def focus(self):
        self._input.focus()

    def watch_size(self, old_size, new_size):
        """React to size changes."""
        # Adjust placeholder based on width
        if new_size.width < 30:
            self._input.placeholder = ">"
        elif new_size.width < 50:
            self._input.placeholder = "Type..."
        else:
            self._input.placeholder = "Type your message..."
