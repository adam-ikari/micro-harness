# src/micro_harness/tui/screens/trust_dialog.py
"""Trust dialog for asking user to trust current directory."""

from textual.screen import ModalScreen
from textual.widgets import Static, Button
from textual.containers import Vertical, Horizontal
import os


class TrustDialog(ModalScreen[bool]):
    """Dialog asking user to trust current directory."""

    DEFAULT_CSS = """
    TrustDialog {
        align: center middle;
    }
    TrustDialog > Vertical {
        width: 60;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }
    TrustDialog .title {
        text-style: bold;
        color: $warning;
        margin-bottom: 1;
    }
    TrustDialog .path {
        color: $primary;
        margin-bottom: 1;
    }
    TrustDialog .description {
        margin: 1 0;
        padding: 1;
        background: $surface-darken-1;
    }
    TrustDialog Button {
        margin: 0 1;
    }
    """

    def __init__(self, lang: str = "en", **kwargs):
        super().__init__(**kwargs)
        self.lang = lang
        self.current_dir = os.getcwd()

    def compose(self):
        if self.lang == "zh":
            title = "🔐 信任当前目录"
            path_label = f"路径: {self.current_dir}"
            desc_title = "信任此目录将允许:"
            desc_items = [
                "• 无需确认即可读取文件",
                "• 无需确认即可写入文件",
                "• 执行此目录中的脚本",
            ]
            trust_text = "信任"
            skip_text = "跳过"
        elif self.lang == "ja":
            title = "🔐 現在のディレクトリを信頼"
            path_label = f"パス: {self.current_dir}"
            desc_title = "このディレクトリを信頼すると:"
            desc_items = [
                "• 確認なしでファイルを読み取り",
                "• 確認なしでファイルを書き込み",
                "• このディレクトリのスクリプトを実行",
            ]
            trust_text = "信頼"
            skip_text = "スキップ"
        else:
            title = "🔐 Trust Current Directory"
            path_label = f"Path: {self.current_dir}"
            desc_title = "Trusting this directory allows:"
            desc_items = [
                "• Read files without confirmation",
                "• Write files without confirmation",
                "• Execute scripts in this directory",
            ]
            trust_text = "Trust"
            skip_text = "Skip"

        description = f"{desc_title}\n" + "\n".join(desc_items)

        yield Vertical(
            Static(title, classes="title"),
            Static(path_label, classes="path"),
            Static(description, classes="description"),
            Horizontal(
                Button(trust_text, id="trust", variant="success"),
                Button(skip_text, id="skip", variant="default"),
            ),
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "trust":
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
