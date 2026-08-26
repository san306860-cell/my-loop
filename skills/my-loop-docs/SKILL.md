---
name: my-loop-docs
description: my-loop v3 的文档化阶段。由 my-loop-pm 在人确认过技术简报和 Medium/Big 分类后派发（通常是子代理）。没有人确认过的 brief 时不要触发。
---

# my-loop-docs · Medium / Big 文档化

输入：人确认过的 brief + 项目现状 + decisions。产出交回 pm：更新的文档、`tickets.json`、`state.json` 初始化。
**文档定义边界（WHAT 和约束），不写 worker 的实现步骤（HOW）。**

## 规矩

1. **只更新本次变更真正涉及的文档。** 没涉及的一个字不动。
2. **契约一个文件，不拆。** 只写「猜错了两边就对不上」的：字段名、类型、必填性、上限、状态码、错误码。改契约先于改代码。
3. **Medium**：相关文档补丁 + 必要契约 + tickets + state。**不写 SPEC。**
4. **Big**：一份 SPEC（骨架用这六段：problem / solution shape / checkable behaviours / settled decisions / testing seams / out-of-scope）+ 契约 + 关键数据流（文字描述，别画会过期的图）+ tickets + state。
5. 与 brief 或 decisions 冲突的地方 → **停下来上报 pm**，不许自行改写。
6. 术语乱的项目可调 `domain-modeling` 理清，但决策一律落 `decisions.jsonl`，不建 ADR。

## 竖切拆票（tickets.json）

- 每条 ticket 是**独立可观察、可验证的竖切**：从用户点得到的动作一路到数据落地。
  自检：**这条做完，人能亲眼看到什么变化？** 答不出来就是切错了。
- 字段只有：`id, goal, acceptance[], depends_on, relevant_docs, domains, status`。多一个都不加。
- **acceptance 必须是可执行命令或明确操作**——pm 收活时要逐条亲自复跑。
  「接口返回 200」不算数；「`curl -s :3000/api/invites … | jq .status` 得到 `accepted`」才算。
- 不塞实现步骤，不写「修改 foo.py 第 281 行」——那是 worker 的 HOW。
- **真实 blocker 才记 `depends_on`**，别为整齐编依赖。
- 初始状态：无依赖的标 `ready`，其余 `todo`。
- 票量以 5±3 条为宜；一条票撑不满一个「人可见变化」就合并进邻票。

## state.json 初始化

`phase` 置 `build` 前置态、`task` 一句话、`classification` 照分类、`current_ticket` 置 null。
写完跑 `python3 ~/.claude/skills/my-loop-pm/hooks/validate_state.py`，报错就修到过。

## 交回清单（给 pm 的回执）

改了哪些文档（路径列表）· 票几条 + 依赖关系一句话 · **你最没把握的一处**（pm 会先抽那里，不许空着）。
