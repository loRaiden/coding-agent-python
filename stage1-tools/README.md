# 阶段 1：可靠的工具系统

## 目标

在阶段 0 的 Agent Loop 基础上，建立可校验、可测试的工具执行层。

当前启用的工具：

- `list_files`：列出目录内容
- `read_file`：读取 UTF-8 文本文件
- `write_file`：创建或覆盖文本文件
- `edit_file`：唯一文本替换
- `glob`：按 glob 模式查找路径
- `grep`：搜索文本并返回文件和行号

所有文件路径都会限制在 Agent 启动时的当前工作目录内。通用 `bash` 暂未启用，因为它需要阶段 3 的权限系统来控制危险命令。

## 运行离线测试

离线测试不调用模型，也不需要 API key：

```bash
cd /d/Raidenshogun/python/Agent
python stage1-tools/test_tools.py
```

也可以使用 unittest 模块运行：

```bash
python -m unittest discover -s stage1-tools -p "test_*.py" -v
```

## 运行 Agent

先安装依赖：

```bash
python -m pip install -r requirements.txt
```

准备配置文件：

```bash
cp .env.example .env
```

然后填写 `.env` 中的 API key、服务地址和模型名，并从项目根目录运行：

```bash
python stage1-tools/agent.py
```

不要提交 `.env`。它已经被 `.gitignore` 忽略，公开仓库只保留 `.env.example`。

## 代码结构

| 文件 | 作用 |
|------|------|
| `tools.py` | 工具实现、路径限制和 Anthropic tool schema |
| `agent.py` | 参数校验、异常收容、结果截断和 Agent Loop |
| `test_tools.py` | 不调用模型的工具层测试 |

## Stage 1 的学习重点

1. 工具 schema 必须和实际函数参数保持一致。
2. 模型传入的参数必须先校验，再执行函数。
3. 工具异常应该作为 `tool_result` 返回给模型，而不是让整个循环崩溃。
4. 大型工具结果必须截断，避免撑爆上下文。
5. 修改文件时，`edit_file` 只允许替换唯一匹配的文本，避免误改多个位置。
