# 技术选型

## 后端

- Python 3.10
- Flask
- Flask-CORS
- OpenAI Python SDK
- httpx
- filelock

选择原因：

- Flask 足够轻量，适合当前少量 API + 静态前端托管
- OpenAI SDK 可直接对接 xi-ai.cn 的 OpenAI 兼容接口
- filelock 能在文件持久化方案下避免并发读写冲突

## 前端

- 原生 HTML / CSS / JavaScript
- Fetch API
- ReadableStream + SSE 文本解析

选择原因：

- handoff 明确要求前端以 HTML 形式实现
- 当前交互集中在流式聊天和少量状态管理，用原生 JS 即可完成
- 无需引入构建工具，直接由 Flask 提供静态文件

## 数据存储

- JSON 文件

目录结构：

- `state.json`：完整用户状态
- `history.json`：用户行为记录
- `llm_log.json`：模型输入输出日志
- `system_log.json`：系统事件日志

选择原因：

- 需求明确不使用数据库
- 单用户、低并发场景下更易调试与交接

## 模型接入

- 服务提供方：xi-ai.cn
- 接口模式：OpenAI Compatible API
- 默认模型：`deepseek-v4-pro`

## 部署形态

- 本地开发：`python backend/app.py`
- 生产入口可继续沿用 WSGI/`gunicorn`，依赖已在 `backend/requirements.txt` 中声明
