# IFI Career Simulator v2

中文职业生涯模拟器。用户先输入姓名，与 AI 角色“小可”完成岗位信息收集，可选补充个人画像，随后进入按节点实时生成的职业剧情，并在结尾得到匹配度、压力、成长三维度回收后的结果分析。

## 当前能力

- 姓名作为会话主键，支持创建、恢复、重置
- 岗位信息收集与画像收集通过 SSE 流式对话完成
- 剧情按节点实时生成，不再一次性生成整段故事
- 基于 JSON 文件持久化 `state/history/llm_log/system_log`
- 前端为纯静态单页页面，由 Flask 直接托管

## 目录

```text
.
├── backend/      # Flask 后端、Prompt、状态模型、服务层
├── frontend/     # 单页前端（index.html / styles.css / app.js）
├── docs/         # 交接、架构、技术选型文档
├── data/users/   # 用户持久化数据
└── backup/       # 旧版本参考，不参与当前实现
```

## 运行

### 1. 创建环境

```bash
conda env create -f environment.yml
conda activate ifi-career-sim
```

### 2. 配置全局环境变量

在启动前先在你的 shell 环境中导出 API Key：

```env
XI_API_KEY=你的 xi-ai.cn API Key
DEEPSEEK_API_KEY=你的 DeepSeek API Key
```

例如：

```bash
export XI_API_KEY="your_xi_key"
export DEEPSEEK_API_KEY="your_deepseek_key"
```

除 API Key 外，其余配置都写在 [backend/config.yaml](/Users/eleven/home/code/AI-product/IFI-Career-Simulator/backend/config.yaml:1)。

### 3. 启动服务

```bash
cd backend
python app.py
```

默认访问地址：`http://localhost:8000`

也可以在启动时直接切换模型提供商参数：

```bash
cd backend
python app.py --provider deepseek --model deepseek-v4-pro --reasoning-effort high --thinking-type enabled --port 8000
```

如果继续使用旧接口：

```bash
cd backend
python app.py --provider xi --port 8000
```

优先级：

- `backend/config.yaml`
- 命令行参数覆盖 `config.yaml`
- API Key 不从 `config.yaml` 读取，只从环境变量读取

如果当前 provider 对应的 API Key 缺失，程序会直接退出。

## API 概览

- `POST /api/users`：创建用户或检查是否存在
- `POST /api/users/<name>/reset`：清空并重新开始
- `GET /api/users/<name>/state`：读取完整状态
- `POST /api/users/<name>/chat/stream`：岗位/画像阶段 SSE 对话
- `POST /api/users/<name>/skip-profile`：跳过画像
- `POST /api/users/<name>/story/next-node`：生成开场、下一节点或结局

## 数据说明

每个用户目录位于 `data/users/<username>/`，主要包含：

- `state.json`：当前完整状态
- `history.json`：用户聊天、剧情选择历史
- `llm_log.json`：发送给模型的 messages 与响应内容
- `system_log.json`：创建、重置、跳过画像等系统事件

## 开发说明

- 前端直接按后端 SSE 事件流渲染，不依赖额外框架
- `backup/` 仅作参考，不应在当前版本中修改
- `backend/agents/` 已预留 Agent 抽象和注册入口，当前默认角色为小可
