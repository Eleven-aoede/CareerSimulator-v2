# 项目交接总结 - IFI Career Simulator v2

> 生成时间: 2026-05-15
> 会话ID: ccbc7937-6a33-4b00-bdb2-46463f72577f

---

## 一、项目概述

这是一个**中文职业生涯模拟器**（"职业穿越游戏"），用户提供岗位信息，可选完成性格画像评估，然后体验 AI 生成的分支叙事，模拟在该岗位的工作体验。AI 角色"小可"（XiaoKe）引导整个流程。

**仓库地址**: https://github.com/Eleven-aoede/CareerSimulator-v2.git

---

## 二、原始任务要求

### 功能需求

1. **实时交互**: 将一次性生成全部剧情改为按节点逐个生成，每次用户选择后实时生成下一个节点（3-8秒/节点，而非等待完整剧情生成超时）
2. **用户状态记录**: 流程开始前请求用户 name，以 name 为 key 维护用户状态、历史交互记录、LLM输入输出记录、系统日志
3. **Resume支持**: 当 username 已存在时，提示用户选择清空历史重新开始或恢复状态继续

### 架构需求

1. **技术栈**: 前端 HTML，后端 Python Flask，conda py3.10 环境，docs 中维护技术选型
2. **README**: 维护功能描述
3. **Git管理**: 中文 commit 消息，中等量级更新后 commit，push 由用户负责
4. **模块化设计**: prompt 单独抽出，预留多 Agent 接口（多角色 + 角色间交互）
5. **存储**: JSON 文件存储，不用数据库

---

## 三、实施计划（5个阶段）

计划文件位于: `.claude/plans/backup-backend-frontend-python-web-1-elegant-token.md`

| 阶段 | 内容 | 状态 |
|------|------|------|
| Phase 1 | 基础框架（conda环境 + Flask骨架 + 持久化 + LLM客户端） | ✅ 已完成 |
| Phase 2 | 信息收集流程（用户路由 + Chat SSE流式传输） | ✅ 已完成 |
| Phase 3 | 实时剧情生成（逐节点引擎 + Prompt模板） | ✅ 已完成 |
| Phase 4 | 前端重写（姓名输入 + Resume流程 + 逐节点模拟器） | ❌ 未完成 |
| Phase 5 | 完善（Agent接口 + 日志 + 文档） | ❌ 未完成 |

---

## 四、已完成的工作

### 4.1 后端文件（全部已创建）

```
backend/
├── app.py                          # Flask应用工厂，注册蓝图，服务前端静态文件
├── config.py                       # 配置（API key, model, 参数, CORS）
├── requirements.txt                # flask, flask-cors, openai, python-dotenv, filelock, gunicorn
├── models/
│   ├── __init__.py
│   └── user_state.py               # UserState/StoryState 数据类 + Phase 枚举
├── routes/
│   ├── __init__.py
│   ├── user.py                     # POST /api/users, POST /api/users/<name>/reset, GET /api/users/<name>/state
│   ├── chat.py                     # POST /api/users/<name>/chat/stream (SSE), POST /api/users/<name>/skip-profile
│   └── story.py                    # POST /api/users/<name>/story/next-node (SSE流式)
├── services/
│   ├── __init__.py
│   ├── llm_client.py               # OpenAI SDK 封装（流式+非流式+日志）
│   ├── conversation.py             # 信息收集对话逻辑，提取标签解析，阶段转换
│   ├── prompt_engine.py            # 构建各阶段的 system prompt + messages
│   ├── persistence.py              # 基于文件的用户状态持久化（FileLock），管理 state.json/history.json/llm_log.json
│   └── story_engine.py             # 核心：逐节点剧情生成引擎（meta+intro, 后续节点, 结局）
├── agents/
│   └── __init__.py                 # 空占位，未实现
├── prompts/
│   ├── story_meta.md               # 生成 meta + intro 节点的 prompt
│   ├── story_node.md               # 生成单个剧情节点的 prompt
│   ├── story_ending.md             # 生成结局的 prompt
│   └── references/
│       ├── story-node-format.md    # 节点结构参考
│       └── option-generation.md    # 选项生成参考
└── utils/
    ├── __init__.py
    └── json_extractor.py           # 从 LLM 响应中提取 JSON
```

### 4.2 其他已创建文件

```
environment.yml                     # conda py3.10 环境定义
.gitignore                          # Python/env/IDE 忽略规则
data/users/.gitkeep                 # 数据目录
```

### 4.3 已有的 Prompt 文件（原有，保留）

```
backend/prompts/
├── xiaoke_base.md                  # 小可角色定义、语气、格式规则
├── phase_job.md                    # 岗位信息收集阶段指令
├── phase_profile.md                # 用户画像收集（9维度，动态提问）
└── phase_story.md                  # 旧版完整剧情生成 prompt（已被拆分替代，可删除）
```

### 4.4 API 路由设计

| 方法 | 路径 | 功能 |
|------|------|------|
| POST | `/api/users` | 创建/检查用户（返回 `new` 或 `exists`） |
| POST | `/api/users/<name>/reset` | 重置用户状态 |
| GET | `/api/users/<name>/state` | 获取完整用户状态 |
| POST | `/api/users/<name>/chat/stream` | 信息收集 SSE 流式聊天 |
| POST | `/api/users/<name>/skip-profile` | 跳过画像阶段 |
| POST | `/api/users/<name>/story/next-node` | 生成下一个剧情节点（SSE流式） |

### 4.5 关键设计决策

- **节点序列固定**: `intro -> node1 -> node2 -> node3 -> taskAction -> taskEmotion -> taskDifficulty -> node4 -> node5 -> __ENDING__`
- **三维评分**: fit（匹配度）、stress（压力）、growth（成长），每次选择小幅累加
- **结局分桶**: 根据最终分数分为 high/mid/low 三档
- **画像影响**: 用户画像影响选项措辞、内心独白、结局分析
- **LLM 配置**: 使用 xi-ai.cn 的 deepseek-v4-pro 模型（OpenAI兼容接口）

---

## 五、未完成的工作

### 5.1 ⚠️ 前端重写（Phase 4 - 最关键）

**当前 `frontend/index.html` 仍是旧版，与新后端完全不兼容。**

旧前端的 API 调用：
- `POST /api/sessions` → 需改为 `POST /api/users`
- `POST /api/sessions/<id>/chat/stream` → 需改为 `POST /api/users/<name>/chat/stream`
- `POST /api/sessions/<id>/generate-story` → 需改为 `POST /api/users/<name>/story/next-node`

前端需要的改动：
1. **新增姓名输入界面** — 作为首屏，输入用户名后调用 POST `/api/users`
2. **新增 Resume 选择对话框** — 当用户名已存在时，显示"继续上次"或"重新开始"选项
3. **移除 Loading 界面** — 不再需要等待完整剧情生成
4. **模拟器改为逐节点渲染** — 每次选择后调用 `/story/next-node` 获取下一节点，而非一次加载完整剧本
5. **状态管理调整** — 适配逐节点累积的数据结构

### 5.2 Agent 接口（Phase 5）

需要创建：
- `backend/agents/base.py` — Agent 抽象基类
- `backend/agents/xiaoke.py` — 小可 Agent 实现
- `backend/agents/registry.py` — Agent 注册中心

### 5.3 日志系统（Phase 5）

- `backend/utils/logger.py` — 统一日志工具
- LLM I/O 日志记录（llm_log.json）— persistence.py 中有接口但未完整使用
- 系统日志记录（system_log.json）

### 5.4 文档（Phase 5）

- `README.md` — 项目功能描述
- `docs/architecture.md` — 架构文档
- `docs/tech-stack.md` — 技术选型文档

### 5.5 Git 提交

**本次会话期间未进行任何 git commit。** 所有改动均为未提交状态。需要：
1. 整理暂存区（大量删除文件 + 新文件）
2. 分批或一次性提交（中文 commit message）

---

## 六、建议的接手顺序

1. **前端重写**（最高优先级）— 没有前端，整个应用无法运行和测试
2. **端到端测试** — 启动后端，验证 API 正常工作
3. **Git commit** — 提交当前所有后端变更
4. **Agent 接口** — 可延后，当前小可角色通过 prompt_engine 直接运作
5. **文档和日志** — 最低优先级

---

## 七、运行方式

```bash
# 创建 conda 环境
conda env create -f environment.yml
conda activate career-simulator

# 配置环境变量
export XI_API_KEY="your_xi_key"
export DEEPSEEK_API_KEY="your_deepseek_key"

# 启动
cd backend
python app.py
# 访问 http://localhost:5000
```

---

## 八、注意事项

- 需要在 shell 全局环境变量中配置真实 API key（`XI_API_KEY` 或 `DEEPSEEK_API_KEY`）
- 旧版文件（`backend/main.py`, `backend/routers/`, `backend/services/session_manager.py` 等）已被删除但未 commit
- `backup/` 目录包含原始参考资料，保留不动
- `backend/prompts/phase_story.md` 是旧版一次性生成的 prompt，已被 `story_meta.md` + `story_node.md` + `story_ending.md` 替代，可考虑删除
