---
name: career-simulator
description: 根据包含岗位信息和用户画像的 JSON 输入，生成可被 HTML 直接读取和运行的职业模拟交互脚本 JSON。
---
# Career Simulator

## 1. 任务定义

1. 读取输入 JSON 中的岗位信息
2. 读取输入 JSON 中的用户画像
3. 按规则生成一份可交互的职业模拟脚本 JSON

最终产物必须是：

- 可被 HTML 直接读取的故事脚本 JSON
- 不是自然语言说明
- 不是给人看的 Markdown
- 不是任务清单式 JSON

## 2. 输入协议

优先接收以下输入结构：

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
      "tags": ["..."]
    },
    "pressure_response": {
      "raw": "...",
      "summary": "...",
      "tags": ["..."]
    },
    "social_energy": {
      "raw": "...",
      "summary": "...",
      "tags": ["..."]
    },
    "authority_style": {
      "raw": "...",
      "summary": "...",
      "tags": ["..."]
    },
    "ambiguity_response": {
      "raw": "...",
      "summary": "...",
      "tags": ["..."]
    },
    "detail_sensitivity": {
      "raw": "...",
      "summary": "...",
      "tags": ["..."]
    },
    "conflict_style": {
      "raw": "...",
      "summary": "...",
      "tags": ["..."]
    },
    "reward_source": {
      "raw": "...",
      "summary": "...",
      "tags": ["..."]
    },
    "drain_source": {
      "raw": "...",
      "summary": "...",
      "tags": ["..."]
    }
  },
  "profile_skipped": false
}
```

输入解释：

- `job_input` 是岗位与公司信息
- `user_profile` 是用户画像
- `profile_skipped` 为 `true` 时，表示用户跳过了画像采集

## 3. 输入处理规则

### 3.1 岗位信息

至少使用这些字段：

- `role_name`
- `job_tasks`
- `industry`
- `company_size`

`additional_context` 可选，但如果存在，应尽量吸收到故事背景中。

### 3.2 用户画像

如果 `profile_skipped` 为 `false`，应让用户画像真实影响：

- 更自然出现的选项措辞
- 节点里的心理活动
- 哪些事件更容易让用户紧张
- 哪些事件更容易让用户获得成就感
- 结局里的匹配分析理由

如果 `profile_skipped` 为 `true`，不要伪造用户画像，不要强行猜测人格。应按“中性默认用户”生成：

- 选项保持均衡
- 心理活动保持普适
- 匹配分析更弱，重点回到岗位本身

## 4. 输出协议

最终输出必须是以下结构：

```json
{
  "meta": {
    "eyebrow": "CAREER SIMULATOR / STORY",
    "title": "职业模拟：{岗位名称}<br />交互脚本",
    "plainTitle": "职业模拟：{岗位名称}",
    "description": "一段简短说明。",
    "settings": [
      { "label": "行业", "value": "..." },
      { "label": "公司规模", "value": "..." },
      { "label": "你的身份", "value": "..." },
      { "label": "故事时段", "value": "..." }
    ]
  },
  "story": {
    "intro": {
      "tag": "背景导入",
      "title": "...",
      "subtitle": "...",
      "paragraphs": ["...", "..."],
      "options": [
        {
          "key": "start",
          "label": "进入这段职业模拟",
          "next": "node1",
          "effect": { "fit": 0, "stress": 0, "growth": 0 }
        }
      ]
    },
    "node1": {
      "tag": "节点 1",
      "title": "...",
      "paragraphs": ["...", "..."],
      "prompt": "...",
      "options": [
        {
          "key": "A",
          "label": "...",
          "next": "node2",
          "effect": { "fit": 1, "stress": 0, "growth": 1 }
        }
      ]
    },
    "taskAction": {
      "tag": "典型任务试做",
      "title": "...",
      "subtitle": "...",
      "paragraphs": ["...", "..."],
      "materials": ["...", "...", "..."],
      "prompt": "...",
      "options": [
        {
          "key": "A",
          "label": "...",
          "next": "taskEmotion",
          "effect": { "fit": 1, "stress": 0, "growth": 1 }
        }
      ]
    },
    "taskEmotion": {
      "tag": "典型任务试做",
      "title": "...",
      "paragraphs": ["..."],
      "prompt": "...",
      "options": [
        {
          "key": "A",
          "label": "...",
          "next": "taskDifficulty",
          "effect": { "fit": 1, "stress": 0, "growth": 1 }
        }
      ]
    },
    "taskDifficulty": {
      "tag": "典型任务试做",
      "title": "...",
      "paragraphs": ["..."],
      "prompt": "...",
      "options": [
        {
          "key": "1",
          "label": "1 分，挺顺手，知道从哪儿下手",
          "next": "__ENDING__",
          "effect": { "fit": 2, "stress": -1, "growth": 0 }
        }
      ]
    }
  },
  "endings": {
    "high": {
      "title": "...",
      "paragraphs": ["...", "..."],
      "matchLabel": "偏高",
      "reason": "..."
    },
    "mid": {
      "title": "...",
      "paragraphs": ["...", "..."],
      "matchLabel": "中等",
      "reason": "..."
    },
    "low": {
      "title": "...",
      "paragraphs": ["...", "..."],
      "matchLabel": "有明显拉扯",
      "reason": "..."
    }
  }
}
```

## 5. 固定生成架构

生成时必须按这个固定架构组织内容：

### 5.1 开场导入

需要交代：

- 岗位所在行业与公司环境
- 用户进入的身份位置
- 第一阶段大致会面对什么节奏

### 5.2 适应事件

必须让用户进入一个真实的第一批工作现场，例如：

- 第一次接到任务
- 第一次参加例会
- 第一次看资料
- 第一次和带教/上级确认方向

### 5.3 典型任务 mini 模拟

必须包含：

- 这个岗位最常见任务的一小段具体现场
- 可处理的原始任务素材
- 三轮固定交互：
  - `taskAction`
  - `taskEmotion`
  - `taskDifficulty`

这个模块默认不改变主分支，但必须在结局中回收。

### 5.4 压力事件

必须出现一个高概率压力源，例如：

- deadline
- 返工
- 模糊需求
- 客户压力
- 指标压力
- 上下游协作不顺

### 5.5 成就或失误事件

必须让用户感受到：

- 这份工作什么地方会有满足感
- 什么地方会让人明显紧绷或消耗

### 5.6 结局

结局必须是描述性的，不是裁判式的。

要说明：

- 用户在这份工作里大概会怎样生活和感受
- 哪些部分顺手
- 哪些部分持续拉扯
- 典型任务体感说明了什么

## 6. 生成流程

### 第一步：提炼岗位画像

从 `job_input` 里提炼：

- 工作节奏
- 典型产出
- 协作结构
- 压力来源
- 成就来源

### 第二步：提炼用户体验倾向

从 `user_profile` 里提炼：

- 更自然的应对方式
- 更容易被触发的压力点
- 更容易获得成就感的反馈
- 更偏好的沟通与行动姿态

### 第三步：做岗位 × 用户交叉判断

必须判断：

- 岗位要求和用户倾向是贴合还是拉扯
- 哪些特质会帮助适应
- 哪些特质会放大压力
- 哪些事件更容易有成就感
- 哪些事件更容易卡住

### 第四步：生成连续职业旅程

必须生成一段“正在发生的职业旅程”，而不是岗位任务清单。

## 7. 硬约束

### 7.1 不能写成任务清单

以下形式视为失败输出：

- `simulation_flow`
- `step_id`
- `scenario + description + options`
- `任务 1 / 任务 2 / 任务 3`
- 把岗位职责逐条改写成选择题

### 7.2 每个关键节点先有场景，再有选择

普通节点不能只写一句任务说明。

要求：

- 除 `intro` 外，普通节点的 `paragraphs` 默认至少 2 段
- 先写眼前发生了什么
- 再写用户此刻什么感觉
- 再进入选择

### 7.3 选择必须是小步动作

不要让用户在一个节点里直接决定：

- 整个项目策略
- 完整职业判断
- 一大段工作周期的总结果

选择应该是：

- 先问谁
- 先看什么
- 先怎么起手
- 先稳节奏还是先推速度

### 7.4 必须有现场感

节点里优先写：

- 办公室、会议室、消息弹窗、走廊、工位
- 身体感受与微动作
- 临场对话
- 任务刚落下来的那个瞬间

不要写成：

- 工作总结
- JD 复述
- 抽象职责列表

## 8. 参考文件

生成前必须读以下两个 reference：

1. `references/story-node-format.md`
2. `references/option-generation.md`

使用方式：

- `story-node-format.md` 负责节点切分、场景铺垫、节奏和 mini 模拟
- `option-generation.md` 负责选项写法、动作粒度、白话程度和选项平衡

`references/profile-intake.md` 不属于当前主流程，不必读取。

## 9. 输出前检查

输出前至少逐项检查：

- 结果是不是 `meta + story + endings`
- 是否仍然偷偷滑回了任务清单结构
- 用户是否能感到“我在现场”
- 每个关键节点是否先有场景，再有选择
- 选项是不是白话、具体、可执行
- 典型任务试做是否真的给了原始材料
- 结局是否回收了 mini 模拟的情绪和难度
- 用户画像是否真实影响了故事
- 如果 `profile_skipped = true`，是否按中性默认逻辑生成，而不是伪造画像
