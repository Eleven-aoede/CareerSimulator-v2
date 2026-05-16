# 技术选型

## 后端

- Python 3.10+
- Flask（轻量 Web 框架 + 静态文件托管）
- Flask-CORS（跨域支持）
- OpenAI Python SDK（对接 LLM 兼容接口）
- filelock（文件级并发控制）

## 前端

- 原生 HTML / CSS / JavaScript（无框架）
- Fetch API + ReadableStream（SSE 流式接收）
- 单文件状态管理 + DOM 操作

## AI / LLM

- **Prompt Engineering**：多阶段 System Prompt 设计（岗位收集 / 画像采集 / 剧情生成）
- **标签协议**：`<extraction>` 触发结构化数据提取与阶段转换，`<options>` 动态生成选项
- **Agent 架构**：角色抽象 + 注册中心，支持多角色扩展
- **流式 JSON 增量解析**：自研状态机（stream_extractor.py），在 LLM 逐 token 输出 JSON 过程中实时提取可渲染字段

## 数据存储

- JSON 文件（无数据库依赖）
- 目录结构：`data/users/<username>/`
  - `state.json`：完整用户状态
  - `history.json`：用户行为记录
  - `llm_log.json`：模型输入输出日志

## 模型接入

- 接口模式：OpenAI Compatible API
- 支持的提供商：DeepSeek、xi-ai.cn
- 默认模型：`deepseek-v4-pro`
- 配置方式：环境变量（API Key） + config.yaml（模型参数）

## 实时通信

- Server-Sent Events (SSE)
- 后端 Flask Generator → `text/event-stream`
- 前端 `response.body.getReader()` 逐块读取解析
- 事件驱动：`token` / `options` / `done` / `stream_title` / `stream_token` / `complete` / `ending`

## 部署

- 开发环境：Flask 内置服务器（`python app.py`）
- 生产建议：gunicorn + gevent（解决 SSE 连接管理问题）
