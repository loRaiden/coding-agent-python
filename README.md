# 手写一个 Coding Agent（Python）

从零手写一个编码 Agent，目标是**吃透原理**，而不是用现成框架跑通一个 demo。

灵感来自 [learn-agents-from-opencode](https://github.com/yexia553/learn-agents-from-opencode)——
那个项目用 TypeScript 讲解 OpenCode 源码；这里我们用 Python 把同样的概念亲手实现一遍。

## 核心理念

一个 Coding Agent 由 6 个模块组成，对应 OpenCode 教程的章节：

| 模块 | OpenCode 章节 | 说明 |
|------|--------------|------|
| Provider | 08 | 调 LLM API、流式输出 |
| System Prompt | 01 | 角色、环境、工具说明的注入 |
| Tool System | 04 | 工具定义、注册、执行 |
| **Agent Loop** | 03 / 05 | ★ 核心决策循环 |
| Permission | 02 | allow / ask / deny |
| Session | 07 | 消息历史、token 控制、上下文压缩 |

其中 **Agent Loop 是心脏**，其余模块是往上加的零件。

## 学习路线（5 个阶段，逐级演进）

| 阶段 | 目录 | 做什么 | 要搞懂的原理 |
|------|------|--------|-------------|
| 0 | `stage0_hello_agent/` | 模型 + 2 个工具 + 循环 | tool-use 协议、消息 role、loop 怎么转 |
| 1 | `stage1_tools/` | 完整工具集（read/write/edit/grep/glob/bash） | 工具注册、参数校验、描述如何影响模型 |
| 2 | `stage2_prompt_context/` | System Prompt 组装 + 上下文管理 | prompt 注入、token 计数、摘要压缩 |
| 3 | `stage3_permission/` | 权限系统 | allow/ask/deny、危险操作拦截 |
| 4 | `stage4_advanced/` | 死循环检测、subagent、流式输出 | doom loop、迭代信息收集 |

**每阶段独立可运行**，建议一个阶段彻底吃透再进下一个。

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置密钥：复制 .env.example 为 .env，填入 ANTHROPIC_API_KEY

# 3. 运行阶段 0
cd stage0_hello_agent
python agent.py
```

## 当前进度

- [x] 阶段 0：最小闭环（模型 + 工具 + 循环）
- [ ] 阶段 1：完整工具集
- [ ] 阶段 2：System Prompt + 上下文
- [ ] 阶段 3：权限系统
- [ ] 阶段 4：进阶特性
