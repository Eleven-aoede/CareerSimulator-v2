# 架构说明

## 总览

项目采用前后端同仓库结构：

- `frontend/`：纯静态单页应用，负责用户名入口、Resume 流程、信息收集聊天、逐节点剧情渲染和结局展示
- `backend/`：Flask API，负责状态管理、Prompt 编排、LLM 调用、实时剧情推进与文件持久化
- `data/users/`：按用户名分目录保存 JSON 状态与日志

## 核心流程

### 1. 用户建立与恢复

1. 前端提交 `POST /api/users`
2. 若用户不存在，后端初始化 `UserState` 并写入欢迎语
3. 若用户已存在，前端展示“继续上次 / 重新开始”
4. 恢复时调用 `GET /api/users/<name>/state`
5. 重置时调用 `POST /api/users/<name>/reset`

### 2. 信息收集

1. 前端向 `POST /api/users/<name>/chat/stream` 发送用户消息
2. 后端 `conversation.process_message_stream` 调用 LLM 流式输出
3. SSE 中的 `token` 事件直接渲染到聊天面板
4. 当模型输出 `<extraction>` 时，后端提取结构化 JSON，推进阶段
5. 阶段从 `job_collection -> profile_collection -> story_simulation`

### 3. 剧情生成

1. 前端在 `story_simulation` 阶段调用 `POST /api/users/<name>/story/next-node`，`action=start`
2. 后端先生成 `meta + intro`
3. 用户选择某个选项后，前端再次调用同一路由并携带 `current_node + choice_key`
4. 后端累加 `fit / stress / growth`，再生成下一节点或结局
5. 当 `next="__ENDING__"` 时转入结局生成并把用户阶段标记为 `completed`

## 状态模型

`UserState` 包含：

- `phase`：当前阶段
- `job_input`：岗位信息结构化结果
- `user_profile`：画像结构化结果
- `conversation_history`：可回放聊天记录
- `story_state`：故事元信息、已生成节点、用户选择、累计分数

`story_state.generated_nodes` 保存已生成节点，便于 Resume 后直接恢复前端渲染。

## 服务层职责

- `services/conversation.py`：处理岗位/画像对话与阶段切换
- `services/story_engine.py`：生成开场、节点和结局
- `services/prompt_engine.py`：拼装 Prompt 与模型输入
- `services/llm_client.py`：封装 OpenAI 兼容接口并记录 LLM 日志
- `services/persistence.py`：持久化状态、历史、日志

## Agent 预留

`backend/agents/` 提供：

- `base.py`：Agent 抽象接口
- `xiaoke.py`：当前默认角色实现
- `registry.py`：注册中心

当前主要用于隔离“角色 prompt 生成”职责，后续可以扩展多角色协作或角色切换。
