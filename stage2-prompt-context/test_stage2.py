import unittest
from pathlib import Path

from context import ContextWindow
from prompt import PromptContext, build_system_prompt, default_prompt_context


class PromptTests(unittest.TestCase):
    def test_prompt_contains_sections_and_tool_descriptions(self):
        prompt = build_system_prompt(
            PromptContext(
                workspace=Path("."),
                tool_guidance="可用工具：\n- read_file: 读取文件。",
                extra_instructions="优先读取相关文件。",
            )
        )
        self.assertIn("当前工作目录：", prompt)
        self.assertIn("read_file: 读取文件", prompt)
        self.assertIn("优先读取相关文件", prompt)
        self.assertIn("信息足够后给出最终回答", prompt)

    def test_default_prompt_lists_schema_tools(self):
        prompt = build_system_prompt(
            default_prompt_context(Path("."), [{"name": "grep", "description": "搜索文本。"}])
        )
        self.assertIn("grep: 搜索文本", prompt)


class ContextTests(unittest.TestCase):
    def test_input_budget_reserves_output_tokens(self):
        context = ContextWindow(max_tokens=100, reserved_output_tokens=25)
        self.assertEqual(context.input_budget, 75)

    def test_tool_turn_is_compacted_as_one_group(self):
        context = ContextWindow(max_tokens=45, reserved_output_tokens=0)
        context.append({"role": "user", "content": "先读取文件"})
        context.append({"role": "assistant", "content": [{"type": "tool_use", "id": "1", "name": "read_file"}]})
        context.append({"role": "user", "content": [{"type": "tool_result", "tool_use_id": "1", "content": "内容"}]})
        context.append({"role": "assistant", "content": "最后结论"})
        context.append({"role": "user", "content": "继续"})
        context.compact_if_needed()
        remaining = context.messages
        serialized = str(remaining)
        self.assertFalse("tool_use" in serialized and "tool_result" not in serialized)

    def test_single_long_message_is_marked_and_bounded(self):
        context = ContextWindow(max_tokens=30, reserved_output_tokens=0)
        context.append({"role": "user", "content": "x" * 500})
        self.assertLessEqual(context.token_count(), 32)
        self.assertIn("消息已截断", context.messages[-1]["content"])

    def test_model_messages_include_summary(self):
        context = ContextWindow(max_tokens=100)
        context.summary = "用户希望修复测试。"
        context.append({"role": "user", "content": "继续处理。"})
        messages = context.model_messages()
        self.assertIn("此前对话摘要", messages[0]["content"])

    def test_invalid_budget_is_rejected(self):
        with self.assertRaises(ValueError):
            ContextWindow(max_tokens=0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
