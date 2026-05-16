# IFI 职业穿越模拟器

一款基于 AI 的中文职业体验模拟器。输入你感兴趣的职业，AI 角色"小可"会带你走进这个岗位的日常，通过互动剧情体验该职业的真实工作场景，最终获得个人匹配度分析。

## 体验流程

1. **输入姓名** — 作为你的旅程存档名，支持中断后恢复
2. **岗位信息收集** — 小可会和你聊几句，了解你想体验的职业（岗位名称、职责、行业、规模等）
3. **个人画像（可跳过）** — 简单了解你的性格偏好，让剧情更贴合你
4. **职业剧情模拟** — 9 个互动节点，每个节点你需要做出选择，剧情实时生成
5. **结局与分析** — 从匹配度、压力、成长三个维度给出结果

## 快速开始

### 环境准备

```bash
conda env create -f environment.yml
conda activate ifi-career-sim
```

### 配置 API Key

在你的 shell 中导出至少一个 LLM API Key：

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

## 功能特点

- **实时流式生成** — 剧情内容逐字呈现，无需等待完整生成
- **跳动小可动画** — 生成过程中小可会跳动提示加载进度
- **断点续玩** — 同一用户名可恢复上次进度，也可选择重新开始
- **多 LLM 支持** — 支持 DeepSeek 和 xi-ai.cn 两个模型提供商
- **文件存储** — 无需数据库，所有数据保存在 `data/users/` 目录

## 目录结构

```
├── backend/          # Flask 后端（路由、服务、Prompt 模板）
├── frontend/         # 单页前端（HTML + CSS + JS，由 Flask 托管）
├── data/users/       # 用户数据目录（自动创建）
├── docs/             # 开发文档
└── environment.yml   # conda 环境定义
```

## 注意事项

- 本项目使用 Flask 开发服务器运行，适合个人使用和演示
- API Key 仅从环境变量读取，不会写入配置文件
- `data/users/` 中的数据为用户隐私，不应提交到 git
