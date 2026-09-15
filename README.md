# my-loop v3

自用的一套「限制 agent」的开发 workflow，跑在 Herdr + 多家 agent CLI（claude / codex / gemini / agy）上。
**人拍全局、AI 干局部；流程全、思想全、实现薄** —— 规矩全部在文件和提示词里，零调度代码。

## 三阶段闭环

```
align   需求对齐+设计   强模型追问 → 人确认技术简报（含反例表，挡/接受由人拍）
                        → 人确认分类 → pm 直接拆竖切票（Big 在简报上多两节：方案形状 / 测试 seam）
build   快速实现        Herdr 拉 build 会话，一次一票（WIP=1），worker 按最简阶梯自定 HOW
                        完成 = 回执贴验收命令真实输出，pm 亲自复跑才记 done
review  强审+沉淀       Herdr 拉全新 review 会话（不看施工过程）三 Pass 强审
                        → 人亲手验收点头 → 才沉淀决策、清理现场、出 ELI5
bug     独立旁路        diagnosing-bugs 诊断 → Bug Brief（复现+根因+红绿回归证明）→ 最小根因修复
```

一条 `decisions.jsonl` 决策库贯穿全程（guard 防改回去、rejected 防决策反转），SessionStart hook 自动注入。
没有文档阶段、没有契约文件：接口只钉 worker 改不动另一边的（对外 API / 共享 schema / 第三方回调），其余由 worker 自定、验收命令圈住。

## 结构

```
skills/my-loop-pm/      总入口：分级、align、拆票、build/review 驱动、bug 旁路、初始化（含项目模板/schema/hooks）
skills/my-loop-worker/  施工规矩：最简阶梯（ponytail 精华）、测试红绿、回执格式（非 Claude 会话由 pm 把全文贴进派工单）
skills/my-loop-review/  强审三 Pass（含变异抽查、收集 ponytail: 天花板标注）
skills/my-loop-eli5/    跟人说话的两种格式（拍板 / 交付），零黑话
```

## 安装

```bash
cp -R skills/* ~/.claude/skills/
```

`~/.claude/settings.json` 注册 hook（同时兼容 v2 老项目的 DECISIONS.md）：

```json
{ "hooks": { "SessionStart": [ { "hooks": [ { "type": "command",
  "command": "python3 ~/.claude/skills/my-loop-pm/hooks/inject_decisions.py" } ] } ] } }
```

依赖（来自 [mattpocock/skills](https://github.com/mattpocock/skills)，拷到 `~/.claude/skills/`）：
`grill-with-docs` + `grilling` + `domain-modeling`（必须）、`diagnosing-bugs`（bug 旁路）、`research` / `tdd`（按需）。

## 用法

1. 在 Herdr 里开一个格子跑 pm 会话（模型自选；build/review 阶段要求 `HERDR_ENV=1`）
2. 项目里说一句「初始化 my-loop v3」（每项目一次）
3. 之后直接说需求。说「有个 bug」自动走 bug 旁路

## 版本

- `v3.1`（当前）：砍掉文档阶段（pm 直接拆票、契约不定死），ponytail 最简阶梯并入 worker，constitution 只留项目特有规矩；四 skill
- `v3.0`：三阶段多模型协议，Herdr 人肉驱动，五 skill + 文件协议
- `v2.1`（tag）：Claude Code 单会话 skill 形态（四步循环 + builder/auditor 子代理）

## 历史证据（docs/）

- `docs/experiments/` — L07 门禁对照实验（触发 7 拦截 0 → 门禁不进手册）与预注册探针
- `docs/v3方案审读-2026-08-26.md` — v3 蓝图四镜头对抗审读报告
- `docs/v3-流程确认-20260826.html` — 人点头过的 V0.1 流程确认稿
- `docs/archive/reins-病类册.md` — 跨项目易错模式与疫苗配方（反例环节的现成弹药）
