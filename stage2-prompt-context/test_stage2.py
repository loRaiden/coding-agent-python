import unittest
from pathlib import Path

from context import ContextWindow
from prompt import PromptContext, build_system_prompt


class PromptTests(unittest.TestCase):
    def test_prompt_contains_workspace_and_instructions(self):
        prompt = build_system_prompt(
            PromptContext(
                workspace=Path("."),
                tool_guidance="可用工具：read_file。",
                extra_instructions="优先读取相关文件。",
            )
        )
        self.assertIn("当前工作目录：", prompt)
        self.assertIn("可用工具：read_file", prompt)
        self.assertIn("优先读取相关文件", prompt)
        self.assertIn("信息足够后给出最终回答", prompt)


class ContextTests(unittest.TestCase):
    def test_token_estimate_and_compaction(self):
        context = ContextWindow(max_tokens=30, summary_max_chars=100)
        context.append({"role": "user", "content": "a" * 80})
        self.assertLessEqual(context.token_count(), 30)

    def test_model_messages_include_summary(self):
        context = ContextWindow(max_tokens=20)
        context.summary = "用户希望修复测试。"
        context.append({"role": "user", "content": "继续处理。"})
        messages = context.model_messages()
        self.assertEqual(messages[0]["role"], "user")
        self.assertIn("此前对话摘要", messages[0]["content"])

    def test_compaction_preserves_latest_message(self):
        context = ContextWindow(max_tokens=20)
        context.append({"role": "user", "content": "x" * 80})
        context.append({"role": "assistant", "content": "latest"})
        self.assertEqual(context.messages[-1]["content"], "latest")


if __name__ == "__main__":
    unittest.main(verbosity=2)
