# 阶段 2：System Prompt 与上下文管理

## 目标

在阶段 1 的工具执行层之上，加入可组合的 system prompt 和受预算控制的消息上下文。

## 代码结构

| 文件 | 作用 |
|------|------|
| `prompt.py` | 组装工作目录、工具说明和行为约束 |
| `context.py` | 估算 token、保存消息、超预算压缩旧消息 |
| `agent.py` | 调用模型、执行工具并使用上下文窗口 |
| `test_stage2.py` | 不调用模型的 prompt 和上下文测试 |

## 运行离线测试

从项目根目录执行：

```bash
python -m unittest discover -s stage2-prompt-context -p "test_*.py" -v
```

## 运行 Agent

```bash
python stage2-prompt-context/agent.py
```

本阶段的 token 估算是教学用的近似值，不等同于具体模型 tokenizer。`ContextWindow` 会从总预算中预留模型输出空间，超出输入预算时按完整消息组压缩旧上下文，避免拆开 assistant 的工具调用和 user 的工具结果；只有单条消息本身过长时才会带标记截断。阶段 3 会在此基础上加入权限决策。
