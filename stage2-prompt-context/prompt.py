from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class PromptContext:
    workspace: Path
    tool_guidance: str
    extra_instructions: str = ""


def build_system_prompt(context: PromptContext) -> str:
    workspace = context.workspace.resolve()
    sections = [
        "你是一个编码助手。",
        f"当前工作目录：{workspace}",
        "所有文件操作都必须限制在当前工作目录内。",
        "需要了解项目时，可以先用 list_files、glob 或 grep，再用 read_file。",
        "只有在用户明确要求时才使用 write_file 或 edit_file。",
        context.tool_guidance.strip(),
    ]
    if context.extra_instructions.strip():
        sections.append(context.extra_instructions.strip())
    sections.append("信息足够后给出最终回答，不要继续调用工具。")
    return "\n\n".join(section for section in sections if section)


def default_prompt_context(workspace: Path, tools: Iterable[dict]) -> PromptContext:
    tool_names = ", ".join(tool["name"] for tool in tools)
    return PromptContext(
        workspace=workspace,
        tool_guidance=f"可用工具：{tool_names}。调用工具前先确认参数完整。",
    )
