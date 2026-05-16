# 项目交接文档 - IFI Career Simulator v2

> 更新时间: 2025-05-16

---

## 一、项目状态

所有核心功能已实现并可运行。前后端联调完成，用户可以完整走通从输入姓名到获得结局分析的全流程。

| 模块 | 状态 |
|------|------|
| Flask 后端 + API 路由 | ✅ |
| 信息收集阶段（SSE 流式对话） | ✅ |
| 动态选项系统（`<options>` 标签） | ✅ |
| 逐节点剧情生成引擎 | ✅ |
| 前端单页应用 | ✅ |
| 流式内容展示（打字机效果） | ✅ |
| 小可头像 + 跳动加载动画 | ✅ |
| 用户断点续玩 | ✅ |
| 文件持久化 | ✅ |
| 前端防闪烁 / 防阶段回退 | ✅ |
| Agent 多角色扩展 | ⬜ 预留接口，未实现多角色 |
| 管理员后台 | ⬜ 计划中 |

---

## 二、架构概览

```
用户浏览器 (frontend/)
    ↕ SSE (Server-Sent Events)
Flask 后端 (backend/app.py)
    ├── routes/user.py      用户创建/恢复/重置
    ├── routes/chat.py      信息收集阶段对话
    ├── routes/story.py     剧情节点生成（SSE 流式）
    ├── agents/
    │   ├── base.py             Agent 抽象基类
    │   ├── xiaoke.py           小可角色（system prompt 构建）
    │   └── registry.py         Agent 注册中心
    ├── services/
    │   ├── conversation.py     对话逻辑 + 标签解析 + 阶段转换
    │   ├── story_engine.py     剧情引擎（meta/节点/结局）
    │   ├── llm_client.py       OpenAI SDK 封装
    │   ├── prompt_engine.py    Prompt 组装
    │   └── persistence.py      文件读写 + FileLock
    └── utils/
        ├── stream_extractor.py   流式 JSON 增量解析器
        └── json_extractor.py     标签内容提取
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

## 三、对话阶段标签协议

### 标签说明

| 标签 | 触发场景 | 后端处理 | 前端行为 |
|------|----------|----------|----------|
| `<extraction>{JSON}</extraction>` | LLM 判断信息收集完成 | 提取 JSON、推进 phase、存储数据 | 不显示，触发阶段切换动画 |
| `<options>["A", "B"]</options>` | 每轮回复末尾 | 解析选项、保留在历史中 | 渲染为可点击选项按钮 |

### 流式解析策略

streaming 过程中实时检测标签前缀，避免将标签内容作为可见文本发送给前端：
- 检测到 `<extraction>` → 停止 token 输出，标记阶段完成
- 检测到 `<options>` → 停止 token 输出，等待流结束后解析选项
- 后备机制：如果 `<options>` 出现在 `<extraction>` 之前阻断了流内检测，流结束后从完整文本中补充提取

---

## 四、前端关键机制

### SSE 事件类型（对话阶段）

| 事件 | 内容 |
|------|------|
| `token` | 逐字符文本内容 |
| `options` | 选项按钮数据 `["选项A", "选项B"]` |
| `done` | 回合结束 `{phase, phase_complete, transition_text}` |

### SSE 事件类型（剧情阶段）

| 事件 | 内容 |
|------|------|
| `progress` | 开始生成提示 |
| `stream_meta` | meta 信息就绪 |
| `stream_title` | 节点标题 |
| `stream_token` | 段落逐字符 |
| `stream_done` | 流式预览结束 |
| `complete` | 完整节点 JSON |
| `ending` | 结局 JSON |
| `error` | 生成失败 |

### 防闪烁 / 防竞态

| 机制 | 说明 |
|------|------|
| 阶段防回退 | `hydrateState()` 比较 PHASE_META 索引，仅允许前进 |
| streaming 跳过刷新 | `refreshState()` 在 streaming 期间不执行 |
| DOM 防重建 | 对话历史未变化时跳过 `rebuildChatStream()` |
| 故事面板防重绘 | `renderStoryPanel()` 在 streaming 期间 return |

---

## 五、Prompt 模板

| 文件 | 阶段 | 功能 |
|------|------|------|
| `xiaoke_base.md` | 全局 | 小可角色人设定义 |
| `phase_job.md` | 岗位收集 | 收集 4 个字段，信息完整时输出 `<extraction>` |
| `phase_profile.md` | 画像采集 | 覆盖 9 个行为维度，确认后输出 `<extraction>` |
| `phase_story.md` | 剧情对话 | 剧情阶段的对话引导 |
| `story_meta.md` | 剧情生成 | 生成 meta + intro 节点 |
| `story_node.md` | 剧情生成 | 生成单个剧情节点 |
| `story_ending.md` | 剧情生成 | 生成结局 |
| `references/story-node-format.md` | 参考 | 节点 JSON 格式规范 |
| `references/option-generation.md` | 参考 | 选项生成规则 |

---

## 六、文件清单

### 后端

| 文件 | 职责 |
|------|------|
| `app.py` | Flask 应用入口，注册蓝图，托管前端静态文件 |
| `config.py` | 配置加载（config.yaml + CLI 参数 + 环境变量） |
| `config.yaml` | 默认配置（模型、参数、端口等） |
| `models/user_state.py` | UserState / StoryState 数据类 + Phase 枚举 |
| `agents/base.py` | Agent 抽象基类 |
| `agents/xiaoke.py` | 小可角色（根据 phase 构建 system prompt） |
| `agents/registry.py` | Agent 注册中心 |
| `services/conversation.py` | 对话流处理 + 标签解析 + 阶段转换 |
| `services/story_engine.py` | 剧情引擎（meta/节点/结局生成） |
| `services/llm_client.py` | OpenAI SDK 封装（流式 + 非流式 + 日志） |
| `services/prompt_engine.py` | 构建各阶段的 messages 列表 |
| `services/persistence.py` | 文件持久化（state/history/llm_log） |
| `utils/stream_extractor.py` | 流式 JSON 增量解析状态机 |
| `utils/json_extractor.py` | 从完整文本提取标签内 JSON |
| `utils/logger.py` | 日志工具 |

### 前端

| 文件 | 职责 |
|------|------|
| `index.html` | 页面结构 |
| `styles.css` | 样式（含小可动画、选项按钮、流式卡片） |
| `app.js` | 全部前端逻辑（状态管理、渲染、SSE 处理、选项交互） |

---

## 七、开发环境

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

## 八、已解决的问题

| 问题 | 根因 | 修复 |
|------|------|------|
| 剧情按钮失效 | `refreshState()` 阻塞 `setStreaming(false)` | 改为 fire-and-forget |
| 前端显示 `<br />` 和 `*` | prompt 含 HTML 标签 + 缺少 markdown 清洗 | 修改 prompt + `_sanitize_token()` |
| 选项闪烁消失 | `refreshState` 触发 DOM 重建 | `pendingOptions` 持久化 |
| 小可跳动不停止 | `pendingAssistantId` 被提前清除 | 全局移除 `.bouncing` |
| 阶段无法转换 | `<options>` 阻断 `<extraction>` 检测 | 流后补充提取 |
| 阶段显示回退 | `refreshState` 返回旧数据覆盖 phase | 阶段索引防回退 |
| 生成中 DOM 闪烁 | `refreshState` 触发全量 DOM 重建 | streaming 期间跳过刷新 + 内容无变化跳过重建 |

---

## 九、待优化项

详见 `docs/roadmap.md`：
1. 流程管理 Agent — 解耦"内容生成"与"阶段决策"
2. 管理员后台 — 校验码登录，查看所有用户日志
