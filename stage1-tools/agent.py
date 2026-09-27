
import os

import anthropic
from dotenv import load_dotenv
from jinja2.utils import missing
from torch.optim.optimizer import required

load_dotenv()  # 读取 .env 里的配置（base_url / auth_token / model）

client = anthropic.Anthropic()  # 自动读取 ANTHROPIC_BASE_URL 和 ANTHROPIC_AUTH_TOKEN
MODEL = os.getenv("ANTHROPIC_MODEL", "deepseek-v4-flash")  # 改成你能访问的模型 ID

# ─────────────────────────────────────────────────────────────
# 1. 工具「定义」：告诉模型你有哪些能力、每种能力需要什么参数。
#    这里只是数据结构，本身不执行任何操作。
#    注意：description 写得好不好，直接决定模型会不会正确选择工具。
# ─────────────────────────────────────────────────────────────
TOOLS = [
    {
        "name": "list_files",
        "description": "列出某个目录下的所有文件和子目录名",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "要列出的目录路径，默认当前目录"},
            },
        },
    },
    {
        "name": "read_file",
        "description": "读取一个文本文件的完整内容",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "要读取的文件路径"},
            },
            "required": ["path"],
        },
    },
]

# ─────────────────────────────────────────────────────────────
# 2. 工具「实现」：真正的执行逻辑。
#    模型只负责「决定调用哪个工具 + 给出参数」，执行是你的代码。
#    name 必须和 TOOLS 里的 name 一一对应。
# ─────────────────────────────────────────────────────────────
def list_files(path: str = ".") -> str:
    try:
        entries = sorted(os.listdir(path))
    except FileNotFoundError:
        return f"错误：目录不存在 {path}"
    return "\n".join(entries) if entries else "(空目录)"


def read_file(path: str) -> str:
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return f"错误：文件不存在 {path}"
    except UnicodeDecodeError:
        return f"错误：{path} 不是文本文件，无法读取"


# name -> 实现函数 的映射，循环里靠它分发
TOOL_FUNCS = {
    "list_files": list_files,
    "read_file": read_file,
}

# ─────────────────────────────────────────────────────────────
# 3. Agentic Loop：整个 Agent 的心脏。
#    模型每轮可能：① 输出文字（结束） ② 输出 tool_use（要调用工具）。
#    只要它还要调工具，就把「工具结果」喂回去，让它基于结果继续推理。
# ─────────────────────────────────────────────────────────────
def run_agent(user_request: str, max_turns: int = 10) -> str:
    system_prompt = (
        "你是一个编码助手。当你需要了解代码或文件时，"
        "先用 list_files 看目录，再用 read_file 读文件。"
        "信息足够后就给出最终回答，不要再调用工具。"
    )
    messages = [{"role": "user", "content": user_request}]

    for turn in range(max_turns):  # 用 max_turns 兜底，防止死循环
        resp = client.messages.create(
            model=MODEL,
            system=system_prompt,
            messages=messages,
            tools=TOOLS,
            max_tokens=1024,
        )

        # 找出本轮所有 tool_use：模型可能一次「并行」调用多个工具（如同时
        # list_files + read_file），每个 tool_use 都必须有对应的 tool_result。
        tool_uses = [b for b in resp.content if b.type == "tool_use"]
        if not tool_uses:
            # 模型不再要工具 → 拼接所有文字块，作为最终答案返回
            text = "".join(b.text for b in resp.content if b.type == "text")
            return text or "(模型没有输出文本)"

        # 关键：先把「模型的决定」整块回填（含 thinking/text/tool_use 原始块），
        # 再为每个 tool_use 都补上对应的 tool_result，二者必须一一对应。
        messages.append({"role": "assistant", "content": resp.content})

        tool_results = []
        for tu in tool_uses:
            print(f" [tool] {tu.name}({tu.input})")
            tool_results.append(excute_toll_call(tu))
        messages.append({"role": "user", "content": tool_results})

    return "（达到最大轮数仍未结束）"

# ─────────────────────────────────────────────────────────────
# 4.对于工具的改进
# ─────────────────────────────────────────────────────────────

#上下文限制
MAX_TOOL_RESULT_CHARS = 8000

def truncate_result(text: str,max_chars:int=MAX_TOOL_RESULT_CHARS)->str:
    if len(text)<=max_chars:
        return text
    keep =(max_chars-80)//2
    omitted=len(text)-keep*2

    return (
        f"{text[:keep]}\n"
        f"... [工具结果已截断，省略{omitted}个字符] ...\n"
        f"{text[-keep:]}"
    )

#对相关问题抛出Error
def validate_tool_input(tool_name:str,raw_input:object)->dict:
    if tool_name not in TOOL_FUNCS:
        raise ValueError(f"未知工具：{tool_name}")

    if not isinstance(raw_input,dict):
        raise ValueError("工具参数必须是 JSON object")

    tool_definition = next(
        tool for tool in TOOLS if tool["name"]==tool_name
    )
    schema= tool_definition["input_schema"]
    properties =schema.get("properties",{})
    required = schema.get("required",[])

    missing = [name for name in required if name not in raw_input]
    if missing:
        raise ValueError(f"缺少必要参数：{','.join(missing)}")
    for name,value in raw_input.items():
        expected_type=properties[name].get("type")

        if expected_type=="string" and not isinstance(value,str):
            raise ValueError(f"参数 {name} 必须是字符串")

    return raw_input

def excute_toll_call(tool_use)->dict:
    try:
        args=validate_tool_input(tool_use.name,tool_use.input)
        result=TOOL_FUNCS[tool_use.name](**args)

        return {
            "type":"tool_result",
            "tool_use_id":tool_use.id,
            "content":truncate_result(str(result)),
        }

    except Exception as exc:
        return {
            "type":"tool_result",
            "tool_use_id":tool_use.id,
            "is_error":True,
            "content":(
                f"工具 {tool_use.name} 执行失败："
                f"{type(exc).__name__}:{exc}"
            ),
        }

if __name__ == "__main__":
    question = "看看当前目录里有什么，读一下 requirements.txt，告诉我这个项目需要哪些依赖"
    print("用户请求：", question)
    print("=" * 60)
    answer = run_agent(question)
    print("=" * 60)
    print("Agent 回答：\n", answer)
