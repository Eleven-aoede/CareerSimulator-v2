# Career Simulator Project

## 项目说明

这个项目用于根据“岗位信息 + 用户画像”的输入 JSON，生成可直接被前端页面读取的职业模拟交互脚本 JSON。

项目当前交付的是一套最小可用包，包含：

- `index.html`
- `career-simulator.skill`
- `references/`
- `README.md`

其中已明确排除 `profile-intake` 相关内容，不在本项目包内。

## 目录结构

```text
project/
├── career-simulator.skill
├── README.md
├── index.html
└── references/
    ├── option-generation.md
    └── story-node-format.md
```

## 文件用途

### `index.html`

前端职业模拟器页面。

作用：

- 读取标准故事脚本 JSON
- 展示分节点职业模拟流程
- 根据用户选择累计 `fit / stress / growth`
- 在结束时输出三档结局之一

### `career-simulator.skill`

职业模拟生成 skill 包。

作用：

- 读取岗位输入 JSON
- 读取用户画像 JSON
- 按固定节点结构生成标准交互脚本

该 skill 的输出目标是标准 JSON，而不是自然语言说明，也不是旧版 `simulation_flow` 线性格式。

### `references/story-node-format.md`

定义故事节点的结构与节奏要求。

重点包括：

- 固定节点顺序
- 每个节点必须先有场景再有选择
- 典型任务 `taskAction / taskEmotion / taskDifficulty` 的写法
- 结局如何回收前面的体验

### `references/option-generation.md`

定义选项写法与数值逻辑。

重点包括：

- 选项必须是白话、具体的小动作
- `effect.fit / effect.stress / effect.growth` 的取值逻辑
- 不同节点适合什么类型的选项
- 分支与下一节点之间的衔接要求

## 输入要求

推荐输入结构如下：

```json
{
  "version": "ifi-profile-input-v1",
  "job_input": {
    "role_name": "...",
    "job_tasks": "...",
    "industry": "...",
    "company_size": "...",
    "additional_context": "..."
  },
  "user_profile": {
    "work_style_preference": {
      "raw": "...",
      "summary": "...",
      "tags": []
    }
  },
  "profile_skipped": false
}
```

说明：

- `job_input` 为必填
- 当 `profile_skipped = false` 时，`user_profile` 应提供完整信息
- 当 `profile_skipped = true` 时，应按中性默认用户生成，不应伪造用户倾向

## 输出要求

标准输出 JSON 结构如下：

```json
{
  "meta": {},
  "story": {
    "intro": {},
    "node1": {},
    "node2": {},
    "node3": {},
    "taskAction": {},
    "taskEmotion": {},
    "taskDifficulty": {},
    "node4": {},
    "node5": {}
  },
  "endings": {
    "high": {},
    "mid": {},
    "low": {}
  }
}
```

不应输出：

- `simulation_flow`
- `step_id`
- 单纯的岗位职责清单
- 只有说明文字、没有标准 JSON 结构的内容

## 使用方式

### 1. 生成故事脚本

使用 `career-simulator.skill`，输入岗位信息 JSON，输出标准职业模拟 JSON。

### 2. 在页面中加载脚本

打开 `index.html`，将生成后的标准 JSON 载入页面，即可进行完整模拟测试。

### 3. 检查重点

测试时建议重点检查：

- 节点顺序是否正确
- 每个节点是否先有场景再有选择
- `taskAction` 是否包含真实素材
- `taskDifficulty` 是否是 1-5 五点评分
- `endings` 是否能回收典型任务中的情绪和难度

## 当前交付边界

本包只包含职业模拟生成与展示所需的核心内容，不包含：

- `profile-intake` 参考文档
- 旧版 `IFI with profile_intake.skill`
- 示例输入输出文件
- 项目管理文档

## 适用场景

适合用于：

- 职业模拟 demo 展示
- skill 交付
- 前端本地联调
- 基于岗位输入生成标准故事脚本的测试
