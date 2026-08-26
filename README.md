# my-loop v2.1

自用的一套「限制 agent」的开发 workflow。**人拍全局、AI 干局部**：
对齐锚 → 反例 → 竖切执行 → 亲手验收，一条决策表贯穿全程。

本版本是 **Claude Code skill 形态**（单会话 + builder/auditor 子代理）。

## 结构

```
skills/my-loop/     主手册 SKILL.md + 项目模板（CURRENT/DECISIONS/SHARED 三个 md）+ 决策注入 hook
agents/             my-loop-builder（施工）、my-loop-auditor（只读验证）两张角色卡
commands/           /my-loop-init（初始化）、/my-loop-lesson（沉淀教训）
```

## 安装

```bash
cp -R skills/my-loop ~/.claude/skills/
cp agents/*.md      ~/.claude/agents/
cp commands/*.md    ~/.claude/commands/
```

再在 `~/.claude/settings.json` 注册 SessionStart hook：

```json
{ "hooks": { "SessionStart": [ { "hooks": [ { "type": "command",
  "command": "python3 ~/.claude/skills/my-loop/hooks/inject_decisions.py" } ] } ] } }
```

项目里执行 `/my-loop-init` 完成初始化，之后直接说需求。

## 沿革

- 对标 [learn-harness-engineering](https://walkinglabs.github.io/learn-harness-engineering/) 十二讲逐条拍板吸收（2026-08-20）
- L07 对照实验：每竖切端到端门禁触发 7 次拦截 0 次 → 不进手册
- 简单性实验：同一功能直接写 2050 行 / 重流程 5461 行，12 条探针打平 → 「流程的钱只花在不做就发现不了的地方」
