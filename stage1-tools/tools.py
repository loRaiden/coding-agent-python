from pathlib import Path

WORKSPACE = Path.cwd().resolve()


def _resolve_path(path: str) -> Path:
    candidate = (WORKSPACE / path).resolve()
    try:
        candidate.relative_to(WORKSPACE)
    except ValueError as exc:
        raise ValueError(f"路径必须位于工作目录内：{path}") from exc
    return candidate


def list_files(path: str = ".") -> str:
    directory = _resolve_path(path)
    if not directory.is_dir():
        raise NotADirectoryError(f"目录不存在：{path}")
    entries = sorted(entry.name + ("/" if entry.is_dir() else "") for entry in directory.iterdir())
    return "\n".join(entries) if entries else "(空目录)"


def read_file(path: str) -> str:
    file_path = _resolve_path(path)
    if not file_path.is_file():
        raise FileNotFoundError(f"文件不存在：{path}")
    return file_path.read_text(encoding="utf-8")


def write_file(path: str, content: str) -> str:
    file_path = _resolve_path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")
    return f"已写入文件：{file_path.relative_to(WORKSPACE)}（{len(content)} 个字符）"


def edit_file(path: str, old_text: str, new_text: str) -> str:
    if not old_text:
        raise ValueError("old_text 不能为空")
    file_path = _resolve_path(path)
    original = read_file(path)
    count = original.count(old_text)
    if count == 0:
        raise ValueError("找不到要替换的文本")
    if count > 1:
        raise ValueError(f"目标文本出现 {count} 次，拒绝进行不明确替换")
    file_path.write_text(original.replace(old_text, new_text, 1), encoding="utf-8")
    return f"已修改文件：{file_path.relative_to(WORKSPACE)}"


def glob(pattern: str, path: str = ".") -> str:
    root = _resolve_path(path)
    if not root.is_dir():
        raise NotADirectoryError(f"目录不存在：{path}")
    matches = sorted(item.relative_to(WORKSPACE).as_posix() for item in root.glob(pattern))
    return "\n".join(matches) if matches else "(没有匹配项)"


def grep(pattern: str, path: str = ".") -> str:
    root = _resolve_path(path)
    if not root.exists():
        raise FileNotFoundError(f"路径不存在：{path}")
    files = [root] if root.is_file() else sorted(item for item in root.rglob("*") if item.is_file())
    matches = []
    for file_path in files:
        try:
            lines = file_path.read_text(encoding="utf-8").splitlines()
        except (UnicodeDecodeError, OSError):
            continue
        for line_number, line in enumerate(lines, start=1):
            if pattern in line:
                relative_path = file_path.relative_to(WORKSPACE).as_posix()
                matches.append(f"{relative_path}:{line_number}:{line}")
    return "\n".join(matches) if matches else "(没有匹配项)"


TOOLS = [
    {
        "name": "list_files",
        "description": "列出工作目录内指定目录的直接子文件和子目录。",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "工作目录内的目录路径，默认当前目录。"},
            },
        },
    },
    {
        "name": "read_file",
        "description": "读取工作目录内的 UTF-8 文本文件。",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "工作目录内的文件路径。"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": "在工作目录内创建或覆盖 UTF-8 文本文件。",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "工作目录内的目标文件路径。"},
                "content": {"type": "string", "description": "要写入的完整文本内容。"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "edit_file",
        "description": "将文件中唯一匹配的一段文本替换为新文本；如果旧文本不存在或出现多次则拒绝修改。",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "工作目录内的文件路径。"},
                "old_text": {"type": "string", "description": "文件中应唯一出现的原文本。"},
                "new_text": {"type": "string", "description": "用于替换的新文本。"},
            },
            "required": ["path", "old_text", "new_text"],
        },
    },
    {
        "name": "glob",
        "description": "在工作目录内按 glob 模式查找路径，例如 **/*.py。",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "相对于 path 的 glob 模式。"},
                "path": {"type": "string", "description": "搜索起始目录，默认当前目录。"},
            },
            "required": ["pattern"],
        },
    },
    {
        "name": "grep",
        "description": "在工作目录内按普通文本查找匹配行，返回文件路径、行号和内容。",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "要搜索的字面文本，不是正则表达式。"},
                "path": {"type": "string", "description": "搜索的文件或目录，默认当前目录。"},
            },
            "required": ["pattern"],
        },
    },
]

TOOLS_FUNCS = {
    "list_files": list_files,
    "read_file": read_file,
    "write_file": write_file,
    "edit_file": edit_file,
    "glob": glob,
    "grep": grep,
}
