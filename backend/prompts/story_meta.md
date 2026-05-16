# 职业模拟 - 生成 Meta + Intro

## 任务

根据输入信息，生成职业模拟的 meta 信息和 intro 开场节点。

## 输入

```json
{input_json}
```

## 输入处理规则

### 岗位信息
至少使用：role_name、job_tasks、industry、company_size。
`additional_context` 如果存在，应吸收到故事背景中。

### 用户画像
如果 `profile_skipped` 为 `false`，intro 的环境描写应轻微贴合用户特质。
如果 `profile_skipped` 为 `true`，用中性视角。

## 生成流程

1. 提炼岗位画像（工作节奏、典型产出、协作结构、压力来源、成就来源）
2. 确定故事背景（具体公司环境、用户身份定位、第一天的氛围）
3. 生成 meta + intro

## 输出格式

直接输出以下 JSON 结构，不要包含任何其他文本：

```json
{
  "meta": {
    "eyebrow": "CAREER SIMULATOR / STORY",
    "title": "职业模拟：{岗位名称}<br />交互脚本",
    "plainTitle": "职业模拟：{岗位名称}",
    "description": "一段简短说明，说明这段模拟的背景。",
    "settings": [
      { "label": "行业", "value": "..." },
      { "label": "公司规模", "value": "..." },
      { "label": "你的身份", "value": "..." },
      { "label": "故事时段", "value": "..." }
    ]
  },
  "intro": {
    "tag": "开场",
    "title": "一句标题",
    "subtitle": "一句副标题",
    "paragraphs": ["第1段：环境和位置", "第2段：这份工作会怎样推着人往前走"],
    "prompt": "一句引导语",
    "options": [
      {
        "key": "A",
        "label": "进入这段职业模拟",
        "next": "node1",
        "effect": { "fit": 0, "stress": 0, "growth": 0 }
      }
    ]
  }
}
```

## intro 节点要求

- 交代行业和公司环境
- 交代用户此时的身份位置
- 交代这一阶段大概会遇到的节奏
- 至少 2 段
- intro 固定只有一个选项："进入这段职业模拟"，next 为 "node1"

## 硬约束

1. 不能写成任务清单
2. 必须有现场感（办公室、会议室、工位）
3. 直接输出 JSON，不要有 markdown 代码围栏或解释文本
