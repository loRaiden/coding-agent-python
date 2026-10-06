from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class PromptContext:
    workspace: Path
    tool_guidance: str
    extra_instructions: str = ""


def build_identity_section() -> str:
    return "你是一个编码助手。"


def build_environment_section(workspace: Path) -> str:
    return f"当前工作目录：{workspace.resolve()}\n所有文件操作都必须限制在当前工作目录内。"


def build_tool_section(tool_guidance: str) -> str:
    return tool_guidance.strip()


def build_behavior_section(extra_instructions: str = "") -> str:
    sections = [
        "需要了解项目时，可以先用 list_files、glob 或 grep，再用 read_file。",
        "只有在用户明确要求时才使用 write_file 或 edit_file。",
    ]
    if extra_instructions.strip():
        sections.append(extra_instructions.strip())
    sections.append("信息足够后给出最终回答，不要继续调用工具。")
    return "\n".join(sections)


def build_system_prompt(context: PromptContext) -> str:
    sections = [
        build_identity_section(),
        build_environment_section(context.workspace),
        build_tool_section(context.tool_guidance),
        build_behavior_section(context.extra_instructions),
    ]
    return "\n\n".join(section for section in sections if section)


def default_prompt_context(workspace: Path, tools: Iterable[dict]) -> PromptContext:
    tool_lines = [
        f"- {tool['name']}: {tool.get('description', '').strip()}"
        for tool in tools
    ]
    return PromptContext(
        workspace=workspace,
        tool_guidance="可用工具：\n" + "\n".join(tool_lines) + "\n调用工具前先确认参数完整。",
    )
