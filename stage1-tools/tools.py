import os

import anthropic
from dotenv import load_dotenv
from huggingface_hub.cli.inference_endpoints import update
from jinja2.utils import missing
from torch.optim.optimizer import required

from pathlib import Path

def read_file(path: str)->str:
    return Path(path).read_text(encoding="utf-8")

def write_file(path: str,content: str)->str:
    Path(path).write_text(content,encoding="utf-8")
    return f"已写入文件：{path}"

def edit_file(path: str,old_text: str,new_text: str)->str:
    file_path=Path(path)
    original=file_path.read_text(encoding="utf-8")

    count=original.count(old_text)

    if count==0:
        raise ValueError("找不到要替换的文本")

    if count>1:
        raise ValueError("目标文件出现多次，拒绝进行不明确替换")

    update=original.replace(old_text,new_text)
    file_path.write_text(update,encoding="utf-8")

    return f"已修改文件：{path}"

def grep(pattern: str,path: str)->str:
    return

def glob(pattern: str)->str:
    return

def bash(command: str)->str:
    return

TOOLS = [

]

TOOLS_FUNCS={
    "read_file": read_file,
    "write_file": write_file,
    "edit_file": edit_file,
    "grep": grep,
    "glob": glob,
    "bash": bash,
}