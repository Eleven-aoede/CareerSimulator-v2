# IFI 职业穿越模拟器

基于 LLM 多轮对话与结构化 Prompt Engineering 的职业体验模拟产品。通过多阶段 System Prompt 引导大模型输出结构化数据，结合 SSE 流式传输实现实时交互，利用自定义标签协议（`<extraction>` / `<options>`）实现 AI 输出的前后端协议化处理，最终为用户生成个性化、可交互的职业模拟剧情。

## 体验流程

1. **输入姓名** — 作为旅程存档名，支持中断后恢复
2. **岗位信息收集** — AI 角色"小可"通过自然对话收集岗位名称、职责、行业、规模
3. **用户画像采集（可跳过）** — 6-8 轮对话覆盖 9 个行为维度，让剧情更贴合个人特质
4. **职业剧情模拟** — 9 个互动节点实时生成，每个节点用户做出选择推进剧情
5. **结局与分析** — 从匹配度、压力、成长三个维度给出个性化结果

## 核心技术亮点

- **多阶段 Prompt 编排** — 每个阶段使用独立 System Prompt，通过 Agent 架构管理角色与阶段切换
- **标签协议驱动阶段转换** — LLM 输出 `<extraction>` 标签触发结构化数据提取和阶段推进
- **SSE 流式生成** — 后端 Generator + 前端 ReadableStream，实现逐 token 打字机效果
- **流式 JSON 增量解析** — 自研状态机在 LLM 输出 JSON 过程中实时提取可渲染内容
- **前后端状态同步** — 防竞态阶段管理，保证 UI 状态与服务端一致

## 快速开始

### 环境准备

```bash
conda env create -f environment.yml
conda activate ifi-career-sim
```

### 配置 API Key

```bash
export DEEPSEEK_API_KEY="your_deepseek_key"
# 或
export XI_API_KEY="your_xi_key"
```

### 启动

```bash
cd backend
python app.py
```

浏览器打开 `http://localhost:8000` 即可使用。

### 命令行参数

```bash
python app.py --provider deepseek --model deepseek-v4-pro --port 8000
```

其余配置见 `backend/config.yaml`。命令行参数优先级高于配置文件。

## 目录结构

```
├── backend/
│   ├── agents/           # Agent 架构（角色管理 + prompt 生成）
│   ├── models/           # 数据模型（UserState, StoryState, Phase）
│   ├── prompts/          # 各阶段 Prompt 模板
│   ├── routes/           # API 路由（user, chat, story）
│   ├── services/         # 核心服务（对话、剧情引擎、LLM 客户端、持久化）
│   └── utils/            # 工具（流式 JSON 解析、标签提取）
├── frontend/             # 单页前端（HTML + CSS + JS，Flask 托管）
├── data/users/           # 用户数据目录（自动创建，已 gitignore）
├── docs/                 # 开发文档
└── environment.yml       # conda 环境定义
```

## 功能特点

- **实时流式生成** — 对话和剧情内容逐字呈现，无需等待完整生成
- **动态选项系统** — LLM 生成选项标签，前端渲染为可点击按钮，降低输入门槛
- **小可跳动动画** — 生成过程中角色头像跳动提示加载状态
- **断点续玩** — 同一用户名可恢复上次进度，也可选择重新开始
- **多 LLM 支持** — 支持 DeepSeek 和 xi-ai.cn 等 OpenAI 兼容接口
- **文件存储** — 无需数据库，JSON 文件持久化所有状态和日志

## 注意事项

- 本项目使用 Flask 开发服务器运行，适合个人使用和演示
- API Key 仅从环境变量读取，不会写入配置文件
- `data/users/` 中的数据为用户隐私，已通过 `.gitignore` 排除
