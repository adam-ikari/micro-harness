# src/zero_agent/tui/widgets/input_box.py
"""Input box widget - user input area."""

from textual.widget import Widget
from textual.widgets import Input
from textual.containers import Horizontal
from textual.reactive import reactive


class InputBox(Horizontal):
    """Input box widget."""

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
