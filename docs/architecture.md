# 架构说明

## 总览

项目采用前后端同仓库结构：

- `frontend/`：纯静态单页应用，负责用户入口、信息收集聊天、剧情渲染和结局展示
- `backend/`：Flask API，负责状态管理、Prompt 编排、LLM 调用、实时剧情推进与文件持久化
- `data/users/`：按用户名分目录保存 JSON 状态与日志

## 核心流程

### 1. 用户建立与恢复

1. 前端提交 `POST /api/users`
2. 若用户不存在，后端初始化 `UserState` 并写入欢迎语
3. 若用户已存在，前端展示"继续上次 / 重新开始"
4. 恢复时调用 `GET /api/users/<name>/state`
5. 重置时调用 `POST /api/users/<name>/reset`

### 2. 信息收集（对话阶段）

1. 前端向 `POST /api/users/<name>/chat/stream` 发送用户消息
2. 后端 `conversation.process_message_stream` 调用 LLM 流式输出
3. SSE 事件类型：
   - `token`：逐字符内容，前端实时渲染
   - `options`：选项按钮数据，前端渲染为可点击按钮
   - `done`：回合结束信号，携带 phase 和 phase_complete 标记
4. 当 LLM 输出 `<extraction>` 标签时，后端提取结构化 JSON 并推进阶段
5. 阶段流转：`job_collection` → `profile_collection` → `story_simulation`

### 3. 标签协议

LLM 输出中嵌入两种自定义标签，由后端解析并转化为前端事件：

| 标签 | 用途 | 前端行为 |
|------|------|----------|
| `<extraction>{...}</extraction>` | 阶段完成信号 + 结构化数据 | 不显示，触发阶段切换 |
| `<options>[...]</options>` | 动态选项列表 | 渲染为可点击按钮 |

标签在对话历史中的处理：
- `<extraction>` 从历史中剥离（仅用于数据提取）
- `<options>` 保留在历史中（LLM 需要上下文），前端显示时过滤

### 4. 剧情生成

1. 前端在 `story_simulation` 阶段调用 `POST /api/users/<name>/story/next-node`
2. 后端先生成 `meta + intro`（故事设定和开场节点）
3. 用户选择某个选项后，前端再次调用同一路由并携带 `current_node + choice_key`
4. 后端累加 `fit / stress / growth` 分数，再生成下一节点或结局
5. 当 `next="__ENDING__"` 时转入结局生成，阶段标记为 `completed`

### 5. 剧情节点序列

```
intro → node1 → node2 → node3 → taskAction → taskEmotion → taskDifficulty → node4 → node5 → __ENDING__
```

## 状态模型

`UserState` 包含：

| 字段 | 说明 |
|------|------|
| `phase` | 当前阶段（Phase 枚举） |
| `job_input` | 岗位信息结构化结果 |
| `user_profile` | 用户画像结构化结果 |
| `conversation_history` | 完整对话历史（含 `<options>` 标签） |
| `story_state` | 故事元信息、已生成节点、用户选择、累计分数 |

## 服务层职责

| 文件 | 职责 |
|------|------|
| `services/conversation.py` | 对话流处理、标签解析、阶段转换 |
| `services/story_engine.py` | 剧情引擎（meta/节点/结局生成） |
| `services/prompt_engine.py` | Prompt 组装（各阶段 system prompt + messages） |
| `services/llm_client.py` | OpenAI 兼容接口封装 + LLM 日志记录 |
| `services/persistence.py` | 文件持久化（state/history/llm_log） |

## Agent 架构

`backend/agents/` 提供角色管理机制：

| 文件 | 职责 |
|------|------|
| `base.py` | Agent 抽象基类 |
| `xiaoke.py` | "小可"角色实现（含各阶段 system prompt 构建） |
| `registry.py` | Agent 注册中心 |

当前通过 `agent_registry.get("xiaoke")` 获取角色实例，由角色负责根据当前 phase 拼装对应的 system prompt。

## 前端状态管理

前端使用单一 `state` 对象管理所有状态，关键防护机制：

- **阶段防回退**：`hydrateState()` 比较 phase 索引，仅允许前进
- **DOM 防闪烁**：streaming 期间跳过 `refreshState` 和面板重绘
- **对话历史去重**：内容未变化时跳过 `rebuildChatStream()`
