from dataclasses import dataclass, field
from typing import Any


@dataclass
class ContextWindow:
    max_tokens: int = 4_000
    summary_max_chars: int = 4_000
    messages: list[dict[str, Any]] = field(default_factory=list)
    summary: str = ""

    def estimate_tokens(self, value: object) -> int:
        # 粗略估算：中英文混合文本按约 4 个字符折算一个 token。
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
        self.messages.append(message)
        self.compact_if_needed()

    def compact_if_needed(self) -> bool:
        if self.token_count() <= self.max_tokens:
            return False

        keep_from = max(0, len(self.messages) - 1)
        older = self.messages[:keep_from]
        self.messages = self.messages[keep_from:]
        if older:
            compacted = self._render_for_summary(older)
            self.summary = self._merge_summary(compacted)
        self._fit_summary_to_budget()
        self._fit_latest_message_to_budget()
        return True

    def _fit_latest_message_to_budget(self) -> None:
        if not self.messages:
            return
        available_tokens = max(1, self.max_tokens - self.estimate_tokens(self.summary))
        message = self.messages[-1]
        content = message.get("content")
        if isinstance(content, str):
            max_chars = available_tokens * 4
            if len(content) > max_chars:
                message["content"] = content[:max_chars]

    def _fit_summary_to_budget(self) -> None:
        message_tokens = self.estimate_tokens(self.messages)
        available_tokens = max(0, self.max_tokens - message_tokens)
        max_chars = available_tokens * 4
        if len(self.summary) > max_chars:
            self.summary = self.summary[-max_chars:] if max_chars else ""

    def _render_for_summary(self, messages: list[dict[str, Any]]) -> str:
        parts = []
        for message in messages:
            role = message.get("role", "unknown")
            content = message.get("content", "")
            parts.append(f"{role}: {content}")
        return "\n".join(parts)

    def _merge_summary(self, new_text: str) -> str:
        merged = f"{self.summary}\n{new_text}".strip() if self.summary else new_text
        if len(merged) <= self.summary_max_chars:
            return merged
        return merged[-self.summary_max_chars :]

    def model_messages(self) -> list[dict[str, Any]]:
        messages = list(self.messages)
        if self.summary:
            return [{"role": "user", "content": f"此前对话摘要：\n{self.summary}"}, *messages]
        return messages
