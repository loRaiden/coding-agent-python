from dataclasses import dataclass, field
from typing import Any


@dataclass
class ContextWindow:
    max_tokens: int = 4_000
    reserved_output_tokens: int = 1_024
    summary_max_chars: int = 4_000
    messages: list[dict[str, Any]] = field(default_factory=list)
    summary: str = ""

    def __post_init__(self) -> None:
        if self.max_tokens <= 0:
            raise ValueError("max_tokens 必须大于 0")
        if self.reserved_output_tokens < 0:
            raise ValueError("reserved_output_tokens 不能小于 0")
        if self.summary_max_chars <= 0:
            raise ValueError("summary_max_chars 必须大于 0")

    @property
    def input_budget(self) -> int:
        return max(1, self.max_tokens - self.reserved_output_tokens)

    def estimate_tokens(self, value: object) -> int:
        if isinstance(value, str):
            return max(1, (len(value) + 3) // 4)
        if isinstance(value, dict):
            return sum(self.estimate_tokens(key) + self.estimate_tokens(item) for key, item in value.items())
        if isinstance(value, (list, tuple)):
            return sum(self.estimate_tokens(item) for item in value)
        return self.estimate_tokens(str(value))

    def token_count(self) -> int:
        return self.estimate_tokens(self.summary) + self.estimate_tokens(self.messages)

    def append(self, message: dict[str, Any]) -> None:
        if not isinstance(message, dict) or "role" not in message:
            raise ValueError("消息必须是包含 role 的对象")
        self.messages.append(message)
        self.compact_if_needed()

    def compact_if_needed(self) -> bool:
        if self.token_count() <= self.input_budget:
            return False

        groups = self._message_groups()
        if len(groups) <= 1:
            self._fit_single_message()
            return True

        keep_count = 1
        while keep_count < len(groups) and self._groups_token_count(groups[keep_count:]) > self.input_budget:
            keep_count += 1
        older = [message for group in groups[:keep_count] for message in group]
        self.messages = [message for group in groups[keep_count:] for message in group]
        self.summary = self._merge_summary(self._render_for_summary(older))
        self._fit_summary_to_budget()
        return True

    def _message_groups(self) -> list[list[dict[str, Any]]]:
        groups: list[list[dict[str, Any]]] = []
        for message in self.messages:
            role = message.get("role")
            if role == "user" and groups and groups[-1][0].get("role") == "assistant":
                groups[-1].append(message)
            elif role == "user" and groups and groups[-1][0].get("role") == "user":
                groups[-1].append(message)
            else:
                groups.append([message])
        return groups

    def _groups_token_count(self, groups: list[list[dict[str, Any]]]) -> int:
        return self.estimate_tokens([message for group in groups for message in group])

    def _fit_single_message(self) -> None:
        if not self.messages:
            return
        message = self.messages[-1]
        content = message.get("content")
        if not isinstance(content, str):
            return
        available = max(1, self.input_budget - self.estimate_tokens(self.summary) - self.estimate_tokens({"role": message.get("role")}))
        marker = "\n... [消息已截断] ..."
        max_chars = max(1, available * 4 - len(marker))
        if len(content) > max_chars:
            truncated = content[:max_chars] + marker
            while max_chars > 1 and self.estimate_tokens({"role": message.get("role"), "content": truncated}) > self.input_budget:
                max_chars = max(1, max_chars - 4)
                truncated = content[:max_chars] + marker
            message["content"] = truncated

    def _fit_summary_to_budget(self) -> None:
        message_tokens = self.estimate_tokens(self.messages)
        available_tokens = max(0, self.input_budget - message_tokens)
        max_chars = min(self.summary_max_chars, available_tokens * 4)
        self.summary = self.summary[-max_chars:] if max_chars else ""

    def _render_for_summary(self, messages: list[dict[str, Any]]) -> str:
        return "\n".join(f"{message.get('role', 'unknown')}: {message.get('content', '')}" for message in messages)

    def _merge_summary(self, new_text: str) -> str:
        merged = f"{self.summary}\n{new_text}".strip() if self.summary else new_text
        return merged[-self.summary_max_chars :]

    def model_messages(self) -> list[dict[str, Any]]:
        messages = list(self.messages)
        if self.summary:
            return [{"role": "user", "content": f"此前对话摘要：\n{self.summary}"}, *messages]
        return messages
