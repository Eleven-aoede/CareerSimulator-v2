# 职业模拟 - 生成单个故事节点

## 任务

根据岗位信息、用户画像、叙事上下文和当前进度，生成指定的故事节点。

## 岗位与用户信息

```json
{input_json}
```

## 当前要生成的节点

节点 ID：`{node_id}`

## 叙事上下文（之前的节点和用户选择）

```json
{narrative_context}
```

## 当前累计分数

```json
{accumulated_scores}
```

## 节点格式参考

{node_format_reference}

## 选项生成规则参考

{option_reference}

## 生成要求

1. 基于用户上一次选择，自然过渡到当前节点
2. 当前节点必须符合其在固定序列中的主题要求
3. 段落先写现场，再写感受，再引向选择
4. 选项必须是白话小动作，2-3 个选项
5. 每个选项的 `next` 字段按固定序列填写下一个节点 ID

## 固定节点序列（用于确定 next）

intro → node1 → node2 → node3 → taskAction → taskEmotion → taskDifficulty → node4 → node5 → __ENDING__

## 输出格式

直接输出以下 JSON 结构，不要包含任何其他文本：

```json
{
  "node_id": "{node_id}",
  "node": {
    "tag": "节点标签",
    "title": "节点标题",
    "subtitle": "节点副标题",
    "paragraphs": ["段落1", "段落2"],
    "materials": [],
    "prompt": "引导用户做选择的一句话",
    "options": [
      {
        "key": "A",
        "label": "选项文字",
        "next": "下一个节点ID",
        "effect": { "fit": 0, "stress": 0, "growth": 0 }
      }
    ]
  }
}
```

## 特殊节点说明

### taskAction
- materials 字段必须有 3 条左右原始素材（具体、可操作）
- prompt 是"你会先怎么处理"

### taskEmotion
- 选项是即时感受，不是策略
- prompt 是"刚做完这一步，你现在什么感觉"

### taskDifficulty
- 固定 5 个选项（1-5分评分）
- 每个选项带白话解释
- next 统一为 "node4"

### node5
- 所有选项的 next 为 "__ENDING__"

## 硬约束

1. 不能写成任务清单
2. 先有场景再有选择
3. 选择必须是小步动作
4. 必须有现场感
5. 直接输出 JSON，不要有 markdown 代码围栏或解释文本
