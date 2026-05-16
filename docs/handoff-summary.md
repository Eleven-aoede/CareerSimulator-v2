# 项目交接文档 - IFI Career Simulator v2

> 更新时间: 2026-05-16

---

## 一、项目状态

所有核心功能已实现并可运行。前后端联调完成，用户可以完整走通从输入姓名到获得结局分析的全流程。

| 模块 | 状态 |
|------|------|
| Flask 后端 + API 路由 | ✅ |
| 信息收集阶段（SSE 流式对话） | ✅ |
| 逐节点剧情生成引擎 | ✅ |
| 前端单页应用 | ✅ |
| 流式内容展示（打字机效果） | ✅ |
| 小可跳动加载动画 | ✅ |
| 用户断点续玩 | ✅ |
| 文件持久化 | ✅ |
| Agent 多角色扩展 | ⬜ 预留接口，未实现 |

---

## 二、架构概览

```
用户浏览器 (frontend/)
    ↕ SSE (Server-Sent Events)
Flask 后端 (backend/app.py)
    ├── routes/user.py      用户创建/恢复/重置
    ├── routes/chat.py      信息收集阶段对话
    ├── routes/story.py     剧情节点生成（SSE 流式）
    ├── services/
    │   ├── conversation.py     对话逻辑 + 阶段转换
    │   ├── story_engine.py     剧情引擎（meta/节点/结局）
    │   ├── llm_client.py       OpenAI SDK 封装
    │   ├── prompt_engine.py    Prompt 组装
    │   └── persistence.py      文件读写 + FileLock
    └── utils/
        ├── stream_extractor.py   流式 JSON 增量解析器
        └── json_extractor.py     完整 JSON 提取
```

### 数据流

1. 前端通过 `fetch` 发起 POST 请求
2. 后端返回 SSE 流（`text/event-stream`）
3. 前端使用 `response.body.getReader()` 逐块读取
4. 每个 SSE 事件格式：`data: {"type": "xxx", ...}\n\n`
5. 前端 `streamJsonEvents(url, body, onEvent)` 统一处理所有 SSE 流

### 剧情节点序列

```
intro → node1 → node2 → node3 → taskAction → taskEmotion → taskDifficulty → node4 → node5 → __ENDING__
```

每个节点由 LLM 实时生成 JSON（含 paragraphs + options），用户选择后触发下一节点。

---

## 三、流式展示实现

### 核心机制

`stream_extractor.py` 实现了增量 JSON 解析的状态机，在 LLM 逐 token 输出 JSON 的过程中，实时提取可展示的内容：

1. **标题提取**：正则匹配 `"title": "..."` 完整闭合后 yield `stream_title` 事件
2. **段落流式**：定位 `"paragraphs": [` 后，逐字符追踪字符串边界，每个字符 yield `stream_token` 事件
3. **状态机状态**：SEARCHING → OUTSIDE_STRING → IN_STRING → ESCAPE

### SSE 事件类型

| 事件 | 触发时机 |
|------|----------|
| `progress` | 开始生成，显示提示文字 |
| `stream_meta` | meta+intro 模式下，meta 信息就绪 |
| `stream_title` | 节点标题完整提取 |
| `stream_token` | 段落内容逐字符 |
| `stream_done` | 流式预览结束 |
| `complete` | JSON 验证通过，权威数据 |
| `ending` | 结局生成完成 |
| `error` | 生成失败 |

### 前端处理

- `showStreamingCard()` — 注入带小可跳动动画的流式卡片
- `updateStreamingCardTitle(title)` — 显示标题
- `appendStreamingToken(index, content)` — 逐字追加段落内容
- `hideStreamingMascot()` — stream_done 时淡出小可
- `complete`/`ending` 事件到达时，用完整数据替换流式卡片

---

## 四、⚠️ 已知问题：SSE 连接阻塞 Bug

**这是当前最大的未修复问题。**

### 现象

在剧情模拟阶段（有时也出现在对话阶段），连续交互 2-3 轮后，发送按钮变为不可点击状态。具体表现：

- 前端 `streamJsonEvents` 中的 `reader.read()` 挂起，永远不返回 `done: true`
- 后续的 `refreshState()` GET 请求无法发出
- 按钮的 `disabled` 状态无法恢复

### 根本原因

Flask（werkzeug）开发服务器在 SSE 生成器 return 后，不一定能及时关闭 HTTP 连接。前端依赖 `reader.read()` 返回 `{done: true}` 来判断流结束，但服务器端连接未关闭时这个信号永远不会到达。

### 已实施的缓解措施

1. **事件处理器返回 `true` 信号终止**：`handleChatEvent` 在收到 `done` 事件时返回 `true`，`handleStoryEvent` 在收到 `complete`/`ending` 时返回 `true`，`streamJsonEvents` 检测到 truthy 返回值后 break 循环
2. **非阻塞 refreshState**：`refreshState().catch(() => {})` 放在 `finally` 块之后而非内部，避免被挂起的 reader 阻塞
3. **移除 reader.cancel()**：曾尝试在 break 后调用 `reader.cancel()`，但这会导致 Flask 收到 BrokenPipeError，阻塞后续请求的处理

### 为什么问题仍然存在

`return true` 机制依赖前端能正确接收和解析到终止事件（`done`/`complete`/`ending`）。在以下场景中会失败：

- SSE 数据块跨越 chunk 边界，终止事件的 JSON 被拆分到两个 chunk 中时解析失败
- Flask 输出缓冲导致终止事件没有被立即 flush
- LLM 响应异常导致后端未 yield 终止事件

### 建议修复方向

1. **替换 Flask 开发服务器**：使用 gunicorn + gevent 或其他异步方案，确保 SSE 连接在生成器结束后立即关闭
2. **前端超时兜底**：在 `reader.read()` 外包一层 `Promise.race` 超时（如 30s），超时后强制结束循环
3. **改用 EventSource API 或第三方 SSE 库**：标准 `EventSource` 对连接生命周期管理更可靠，但不支持 POST
4. **心跳机制**：后端定期发送 `ping` 事件，前端检测心跳超时则主动断开

---

## 五、文件清单

### 后端核心

| 文件 | 职责 |
|------|------|
| `backend/app.py` | Flask 应用入口，注册蓝图，托管前端静态文件 |
| `backend/config.py` | 配置加载（config.yaml + CLI 参数 + 环境变量） |
| `backend/config.yaml` | 默认配置（模型、参数、端口等） |
| `backend/models/user_state.py` | UserState / StoryState 数据类 + Phase 枚举 |
| `backend/services/story_engine.py` | 剧情引擎：生成 meta+intro / 节点 / 结局 |
| `backend/services/conversation.py` | 信息收集对话逻辑 + 阶段转换判断 |
| `backend/services/llm_client.py` | OpenAI SDK 封装（流式 + 非流式 + 日志记录） |
| `backend/services/prompt_engine.py` | 构建各阶段的 system prompt + messages |
| `backend/services/persistence.py` | 文件持久化（state/history/llm_log/system_log） |
| `backend/utils/stream_extractor.py` | 流式 JSON 增量解析状态机 |
| `backend/utils/json_extractor.py` | 从 LLM 响应提取完整 JSON |

### Prompt 模板

| 文件 | 用途 |
|------|------|
| `backend/prompts/story_meta.md` | 生成 meta + intro 节点 |
| `backend/prompts/story_node.md` | 生成单个剧情节点 |
| `backend/prompts/story_ending.md` | 生成结局 |
| `backend/prompts/xiaoke_base.md` | 小可角色定义 |
| `backend/prompts/phase_job.md` | 岗位信息收集 |
| `backend/prompts/phase_profile.md` | 画像收集 |

### 前端

| 文件 | 职责 |
|------|------|
| `frontend/index.html` | 页面结构 |
| `frontend/styles.css` | 样式（含流式卡片 + 小可跳动动画） |
| `frontend/app.js` | 全部前端逻辑（状态管理、渲染、SSE 处理） |

---

## 六、开发环境

```bash
conda env create -f environment.yml
conda activate ifi-career-sim

export DEEPSEEK_API_KEY="your_key"
cd backend && python app.py
# http://localhost:8000
```

### 切换模型

```bash
python app.py --provider deepseek --model deepseek-v4-pro
python app.py --provider xi --model deepseek-v4-pro
```

---

## 七、扩展方向

- **Agent 多角色**：`backend/agents/` 已预留目录，可实现不同引导角色
- **生产部署**：替换 Flask 开发服务器为 gunicorn（同时解决 SSE 阻塞问题）
- **更多职业模板**：丰富 prompt 中的行业参考素材
- **评分细化**：当前三维评分较粗糙，可结合用户画像做更细粒度的匹配分析
