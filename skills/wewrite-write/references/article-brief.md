# 文章任务书与主张清单

正文动笔前必须先保存 `brief.yaml` 和 `claims.yaml`。它们让“写得像一篇文章”变成
“解决一个明确的读者问题”。字段可补充，但不能省略核心项。

## brief.yaml

```yaml
version: 1
audience:
  who: "具体读者"
  context: "读者在什么情境下阅读"
  question: "读者真正要解决的问题"
goal:
  takeaway: "读完能复述的一个结论"
  action: "读完可以采取的行动；纯观点文可写判断方法"
thesis:
  statement: "全文核心判断"
  novelty: "相较常见说法新增了什么"
  boundary: "结论在什么条件下成立"
  counterpoint: "最强反方或替代解释"
personal_materials:
  available: false
  items: []                 # 只记录用户在本次任务明确提供的经历、观察或原话
framework: "观点"
sections:
  - purpose: "本节推进什么"
    claim_ids: [C1]
constraints:
  desired_length: "1200-2500 字"
  must_include: []
  must_avoid: []
```

`novelty` 不是强行唱反调。找不到可靠的新角度时，缩小问题、补充适用条件或提供更好用的
判断框架。`action` 必须与题目相称，不为凑“干货”制造步骤。

## claims.yaml

```yaml
version: 1
claims:
  - id: C1
    text: "正文准备表达的主张"
    type: fact              # fact / inference / opinion / user_experience
    source_ids: []          # 对应 sources.yaml 的 id；意见可为空
    status: supported       # supported / bounded / unsupported
    boundary: "适用范围或不确定性"
```

- `fact` 必须有能直接支持它的来源；否则删除或标为 `unsupported`，不得进入正文。
- `inference` 要列出依据并明确这是推断；`opinion` 不伪装成共识。
- `user_experience` 只能来自本次任务里用户明确提供的材料，并在来源账本标为
  `user_provided`。范文、模型记忆和人格示例都不是用户经历。
- 每一节至少服务一个主张；无法对应主张的段落默认删除。

## 个人材料边界

`personal_materials.available=false` 时，可以写“我认为”“我的判断是”这类作者判断，不能写
作者经历过的事件、朋友或同事、现场对话、动作、时间地点和感官细节。人格要求私人开场或
故事开场时，自动改为观察、问题或核心判断开场，不得补造材料。
