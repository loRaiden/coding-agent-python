import os

import tools
from context import ContextWindow
from prompt import build_system_prompt, default_prompt_context
from tools import TOOLS, TOOLS_FUNCS

MAX_TOOL_RESULT_CHARS = 8_000


def truncate_result(text: str, max_chars: int = MAX_TOOL_RESULT_CHARS) -> str:
    if len(text) <= max_chars:
        return text
    marker = "\n... [工具结果已截断] ...\n"
    keep = max(0, (max_chars - len(marker)) // 2)
    return f"{text[:keep]}{marker}{text[-keep:] if keep else ''}"


def validate_tool_input(tool_name: str, raw_input: object) -> dict:
    tool = next((item for item in TOOLS if item["name"] == tool_name), None)
    if tool is None or tool_name not in TOOLS_FUNCS:
        raise ValueError(f"未知工具：{tool_name}")
    if not isinstance(raw_input, dict):
        raise ValueError("工具参数必须是 JSON object")

    schema = tool["input_schema"]
    properties = schema.get("properties", {})
    required = schema.get("required", [])
    missing = [name for name in required if name not in raw_input]
    if missing:
        raise ValueError(f"缺少必填参数：{', '.join(missing)}")
    unexpected = sorted(set(raw_input) - set(properties))
    if unexpected:
        raise ValueError(f"未知参数：{', '.join(unexpected)}")
    for name, value in raw_input.items():
        if properties[name].get("type") == "string" and not isinstance(value, str):
            raise ValueError(f"参数 {name} 必须是字符串")
    return raw_input


def execute_tool_call(tool_use) -> dict:
    try:
        args = validate_tool_input(tool_use.name, tool_use.input)
        result = TOOLS_FUNCS[tool_use.name](**args)
        return {"type": "tool_result", "tool_use_id": tool_use.id, "content": truncate_result(str(result))}
    except Exception as exc:
        return {
            "type": "tool_result",
            "tool_use_id": tool_use.id,
            "is_error": True,
            "content": f"工具 {tool_use.name} 执行失败：{type(exc).__name__}: {exc}",
        }


def run_agent(
    user_request: str,
    max_turns: int = 10,
    max_context_tokens: int = 4_000,
    max_output_tokens: int = 1_024,
) -> str:
    try:
        import anthropic
        from dotenv import load_dotenv
    except ImportError as exc:
        raise RuntimeError("运行 Agent 需要安装依赖：python -m pip install -r requirements.txt") from exc

    load_dotenv()
    client = anthropic.Anthropic()
    model = os.getenv("ANTHROPIC_MODEL", "deepseek-v4-flash")
    prompt_context = default_prompt_context(tools.WORKSPACE, TOOLS)
    system_prompt = build_system_prompt(prompt_context)
    context = ContextWindow(
        max_tokens=max_context_tokens,
        reserved_output_tokens=max_output_tokens,
    )
    context.append({"role": "user", "content": user_request})

    for _ in range(max_turns):
        response = client.messages.create(
            model=model,
            system=system_prompt,
            messages=context.model_messages(),
            tools=TOOLS,
            max_tokens=max_output_tokens,
        )
        tool_uses = [block for block in response.content if block.type == "tool_use"]
        if not tool_uses:
            text = "".join(block.text for block in response.content if block.type == "text")
            if response.stop_reason == "max_tokens":
                return text + "\n\n[警告：模型输出达到 max_tokens，回答可能不完整]"
            return text or "(模型没有输出文本)"

        context.append({"role": "assistant", "content": response.content})
        results = []
        for tool_use in tool_uses:
            print(f"[tool] {tool_use.name}({tool_use.input})")
            results.append(execute_tool_call(tool_use))
        context.append({"role": "user", "content": results})

    return f"达到最大工具调用轮数（{max_turns}），任务未完成。"


if __name__ == "__main__":
    question = "列出当前目录，并读取 requirements.txt，告诉我项目需要哪些依赖。"
    print("用户请求：", question)
    print("=" * 60)
    print("Agent 回答：\n", run_agent(question))
