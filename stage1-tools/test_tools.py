import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import agent
import tools


class ToolTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name).resolve()
        self.workspace_patch = patch.object(tools, "WORKSPACE", self.workspace)
        self.workspace_patch.start()

    def tearDown(self):
        self.workspace_patch.stop()
        self.temp_dir.cleanup()

    def test_write_read_and_edit_file(self):
        tools.write_file("nested/example.txt", "hello world")
        self.assertEqual(tools.read_file("nested/example.txt"), "hello world")
        tools.edit_file("nested/example.txt", "world", "agent")
        self.assertEqual(tools.read_file("nested/example.txt"), "hello agent")

    def test_edit_rejects_ambiguous_text(self):
        tools.write_file("repeat.txt", "same same")
        with self.assertRaisesRegex(ValueError, "出现 2 次"):
            tools.edit_file("repeat.txt", "same", "new")

    def test_paths_cannot_escape_workspace(self):
        with self.assertRaisesRegex(ValueError, "工作目录内"):
            tools.read_file("../outside.txt")

    def test_glob_and_grep(self):
        tools.write_file("src/one.py", "needle here\nsecond line")
        tools.write_file("src/two.txt", "nothing")
        self.assertEqual(tools.glob("**/*.py"), "src/one.py")
        self.assertEqual(tools.grep("needle"), "src/one.py:1:needle here")

    def test_tool_schemas_match_implementations(self):
        schema_names = {item["name"] for item in tools.TOOLS}
        self.assertEqual(schema_names, set(tools.TOOLS_FUNCS))
        self.assertNotIn("bash", schema_names)

    def test_executor_reports_missing_arguments(self):
        tool_use = SimpleNamespace(name="read_file", input={}, id="call-1")
        result = agent.execute_tool_call(tool_use)
        self.assertTrue(result["is_error"])
        self.assertIn("缺少必填参数", result["content"])

    def test_executor_reports_unknown_arguments(self):
        tool_use = SimpleNamespace(
            name="read_file", input={"path": "x.txt", "extra": True}, id="call-2"
        )
        result = agent.execute_tool_call(tool_use)
        self.assertTrue(result["is_error"])
        self.assertIn("未知参数", result["content"])

    def test_executor_reports_unknown_tool(self):
        tool_use = SimpleNamespace(name="not_a_tool", input={}, id="call-3")
        result = agent.execute_tool_call(tool_use)
        self.assertTrue(result["is_error"])
        self.assertIn("未知工具", result["content"])

    def test_executor_truncates_tool_result(self):
        with patch.dict(tools.TOOLS_FUNCS, {"read_file": lambda path: "x" * 100}):
            tool_use = SimpleNamespace(name="read_file", input={"path": "x.txt"}, id="call-4")
            result = agent.execute_tool_call(tool_use)
        self.assertLessEqual(len(result["content"]), agent.MAX_TOOL_RESULT_CHARS)
        self.assertIn("工具结果已截断", result["content"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
