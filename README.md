# my-loop v3

自用的一套开发 workflow，跑在当前宿主或 Herdr + 多家 agent CLI（claude / codex / gemini / agy / pi / dsh…）上。
**用户定目标与验收，PM 管证据，执行者定实现** —— 规矩全部在文件和提示词里，零调度代码。

## 闭环

```
align   对齐与准备   明确 Goal/DoD/Boundary/Constraints/反例 → 记 brief
                     → 问一次验收方式（notify / self）记进 review_policy
                     → PM 直接拆票（Big 在 brief 多两节：方案形状 / 测试边界）
build   实施与对账   一次一票（WIP=1），worker 按最简阶梯自定 HOW
                     回执给真实证据，PM 逐条核对才记 done
accept  验收与收尾   notify → 等用户 review；self → PM 按 my-loop-review 组织审阅
                     必需标准全过 + review_evidence 落地，才算交付完成
bug     诊断与修复   diagnosing-bugs 建立可证伪证据 → Bug Brief → 根因修复
```

一条 `decisions.jsonl` 决策库贯穿全程（guard 防改回去、rejected 防决策反转），SessionStart hook 自动注入。
项目规则以 `AGENTS.md` 为准，`CLAUDE.md` 只留一行兼容引用，不维护第二份正文。
没有独立文档阶段、没有另造的契约文件：接口只钉 worker 改不动另一边的（对外 API / 共享 schema / 第三方回调），其余由 worker 选择、acceptance 与既有代码约束。
`validate_state.py` 是机器闸门：进验收前没 `review_policy`、标 done 没 `review_evidence` 或还有票没完成，一律红。

## 结构

```
skills/my-loop-pm/      总入口：分级、对齐、拆票、派工对账、验收收尾、诊断旁路、初始化（含项目模板/schema/hooks）
skills/my-loop-worker/  施工规矩：最简阶梯（ponytail 精华）、测试与证据、回执格式（宿主不支持加载时由 PM 贴全文）
skills/my-loop-review/  审阅与验收：授权边界、变异抽查、收集 ponytail: 天花板标注、按 review_policy 收尾
skills/my-loop-eli5/    跟用户说话的两种格式（Decision / Closure），先给结论
```

## 安装

```bash
./install.sh   # 装到本机所有 agent 的 skill 区（公用区 + codex/pi/dsh/devin/cursor/mirasim/gemini），幂等
```

`~/.claude/settings.json` 注册 hook（老项目的 `DECISIONS.md` 继续认，不必迁移）：

```json
{ "hooks": { "SessionStart": [ { "hooks": [ { "type": "command",
  "command": "python3 ~/.claude/skills/my-loop-pm/hooks/inject_decisions.py" } ] } ] } }
```

按需依赖（来自 [mattpocock/skills](https://github.com/mattpocock/skills)）：`grilling`、`domain-modeling`、`research`、`diagnosing-bugs`。
用 Herdr 派工时另需 `herdr` skill；只用当前宿主则不需要。

## 用法

1. 开一个会话跑 pm（当前宿主或 Herdr 格子都行，PM 会问一次）
2. 项目里说一句「初始化 my-loop」（每项目一次，写进 `AGENTS.md`）
3. 之后直接说需求。PM 会问一次这次怎么验收（notify / self），之后同类任务沿用

## 版本

- `v3.2`（当前）：合并 AGENTS.md 路线与 `review_policy` 验收协议（notify / self）+ 机器闸门；砍掉独立文档阶段（PM 直接拆票、内部接口不定死）；ponytail 最简阶梯并入 worker；constitution 只留项目特有约束。四 skill
- `v3.1`（未发布，已并入 v3.2）：砍文档阶段 + ponytail 并入
- `v3.0`：三阶段多模型协议，Herdr 人肉驱动，五 skill + 文件协议
- `v2.1`（tag）：Claude Code 单会话 skill 形态（四步循环 + builder/auditor 子代理）

## 历史证据（docs/）

- `docs/experiments/` — L07 门禁对照实验（触发 7 拦截 0 → 门禁不进手册）与预注册探针
- `docs/v3方案审读-2026-08-26.md` — v3 蓝图四镜头对抗审读报告
- `docs/v3-流程确认-20260826.html` — 人点头过的 V0.1 流程确认稿
- `docs/archive/reins-病类册.md` — 跨项目易错模式与疫苗配方（反例环节的现成弹药）
