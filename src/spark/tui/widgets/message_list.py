# src/spark/tui/widgets/message_list.py
"""Message list widget - scrollable conversation history."""

from textual.widget import Widget
from textual.message import Message
from textual.containers import ScrollableContainer


class MessageList(ScrollableContainer):
    """Message list widget with scrollable conversation history."""

    DEFAULT_CSS = """
    MessageList {
        height: 1fr;
        overflow-y: auto;
        padding: 1;
    }
    """

    class MessageAdded(Message):
        """Message added event."""
        def __init__(self, message_id: str):
            self.message_id = message_id
            super().__init__()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._message_count = 0

    def add_user_message(self, content: str) -> str:
        """Add user message."""
        from spark.tui.widgets.message_item import UserMessage
        msg_id = f"user_{self._message_count}"
        self._message_count += 1
        self.mount(UserMessage(content, id=msg_id))
        self._scroll_to_bottom()
        return msg_id

    def add_assistant_message(self, content: str = "") -> str:
        """Add assistant message."""
        from spark.tui.widgets.message_item import AssistantMessage
        msg_id = f"assistant_{self._message_count}"
        self._message_count += 1
        msg = AssistantMessage(content, id=msg_id)
        self.mount(msg)
        self._scroll_to_bottom()
        return msg_id

    def add_tool_message(self, tool_name: str, args: dict, status: str = "pending") -> str:
        """Add tool message."""
        from spark.tui.widgets.message_item import ToolMessage
        msg_id = f"tool_{self._message_count}"
        self._message_count += 1
        msg = ToolMessage(tool_name, args, status, id=msg_id)
        self.mount(msg)
        self._scroll_to_bottom()
        return msg_id

    def _scroll_to_bottom(self):
        """Scroll to bottom of message list."""
        try:
            self.scroll_end(animate=False)
        except Exception:
            pass

    def update_message(self, msg_id: str, content: str):
        """更新消息内容。"""
        try:
            msg = self.query_one(f"#{msg_id}")
            if hasattr(msg, "update_content"):
                msg.update_content(content)
        except Exception:
            pass

    def update_tool_status(self, msg_id: str, status: str, result: str = ""):
        """更新工具状态。"""
        try:
            msg = self.query_one(f"#{msg_id}")
            if hasattr(msg, "update_status"):
                msg.update_status(status, result)
        except Exception:
            pass

    def clear(self):
        """清空所有消息。"""
        self.remove_children()
        self._message_count = 0
