# my-loop v3

一套可在当前宿主或多 Agent 环境中使用的开发工作流。用户定目标与验收，PM 管目标和证据，worker 负责实现，reviewer 核对实际产物。

## 怎么用

新任务直接说「用 my-loop 帮我做……」。项目 `AGENTS.md` 已声明使用 my-loop 时，之后可直接说需求。已有授权、验收方式和工具选择继续沿用，只补问会影响目标、关键行为或授权的缺失信息。

简单任务可在当前会话完成，不强制创建整套状态文件。需要持续派工的任务使用 brief、tickets、实施回执和 review；没有额外的方法论打卡阶段。

| 环节 | 工作与依据 |
|---|---|
| 对齐与设计 | PM 明确目标、边界和验收；按问题使用 Release It!、DDIA、PoEAA。关键决定互相依赖时，使用 Wayfinder 的本地适配梳理 |
| 实现 | Worker 固定使用 Code Complete、A Philosophy of Software Design 和项目规则；回执把关键选择关联到代码位置、理由和验证依据 |
| 技术核对 | Reviewer 固定使用 Refactoring，沿代码、调用链和检查结果核对 worker 的主张；「已读」或笼统的「测试通过」不代替证据 |
| 最终验收 | `notify` 和 `self` 都先做必要技术核对；前者等用户验收，后者由 PM 按已定标准验收 |

方法论通常先读 mini，需要时再查完整规则。简洁按理解、修改和验证的总成本判断，不按最少行数或文件数打分。多个方法可以共用一条实际约束和证据。

TasteSkill v2 按需用于网页视觉与交互设计；图片、动效数量不作为通用验收标准。Wayfinder 的原版保留供单独调用，PM 使用 [本地适配](skills/my-loop-pm/references/wayfinder.md)。完整分工见 [方法论路由](skills/my-loop-pm/references/methodology-routing.md)。这些 Skill 也可以单独点名使用。

## 安装与更新

需要 Bash 和 Python 3.10+。仓库包含 13 个 Skill：四个 my-loop 角色、六套书籍方法论、TasteSkill v2、Wayfinder、适配后的 Ponytail；安装不需要临时下载依赖。

```bash
./install.sh --dry-run  # 预览
./install.sh            # 安装或同步当前 checkout
./install.sh --check    # 检查正文和链接是否与当前 checkout 一致
```

更新已安装版本时，先将此仓库更新到希望使用的提交，再运行 `./install.sh`。

运行时正文统一存放在 `~/.agents/skills/<name>/`。Codex、Claude 及检测到的已安装宿主使用指向它的链接；仓库 `skills/` 是可版本管理、可复现的分发快照。以后修改共享正文，所有兼容入口同时读到同一份内容；发布这些修改时再同步回仓库。

| 宿主 | 兼容入口 |
|---|---|
| Codex / Claude | `~/.codex/skills`、`~/.claude/skills`；同时支持当前 `CODEX_HOME/skills` |
| Cursor | `~/.cursor/skills` |
| Pi | `~/.pi/agent/skills` |
| Devin | `~/.config/devin/skills`、`~/.config/cognition/skills` |
| Dsh | `~/.dsh/skills` |
| agy / Antigravity CLI | `~/.gemini/config/skills` |
| Kiro | `~/.kiro/skills` |
| WorkBuddy / CodeBuddy | 各自的 `~/.workbuddy/skills`、`~/.codebuddy/skills` |

可选宿主按已有配置目录识别。旧版本创建的 `~/.pi/skills`、`~/.devin/skills`、`~/.mirasim/skills` 若仍存在，也转为链接，避免留下旧副本；这不表示所有旧路径都被当前宿主加载。整目录已链接共享区时不会再次创建自环链接。

替换前，原有目录、链接及退役的 `my-loop-docs` / `my-loop-eli5` 会移至 `~/.agents/backups/my-loop/<时间-编号>/`，`manifest.json` 记录原位置。无关 Skill 不变；重复运行无差异时不重写、不新增备份。`--dry-run` 和 `--check` 都不写文件。`--home <目录>` 可在独立目录验证安装，不改当前用户的安装。

文件同步不等于已经替换旧会话内读过的上下文。新任务会读取新入口；已有会话需要重新加载 Skill 或新开会话。Kiro CLI 自定义 Agent 还应保留默认资源继承；项目私有 Skill 或自定义搜索路径由该项目配置决定。

## 项目状态与决策

项目规则以 `AGENTS.md` 为准，`CLAUDE.md` 只作兼容引用。决策集中记录在 `.my-loop/decisions.jsonl`；新记录用 `source` 区分用户决定、项目约束和授权内工程选择，旧记录不推定已获用户确认。空 JSONL 不会遮住同层旧版 `DECISIONS.md`。

`validate_state.py` 检查阶段、WIP、依赖和验收方式；完成票及最终验收的回执必须是可读、非空的文件。文件检查不证明内容真实或覆盖充分，reviewer 仍需核对。

Claude Code 可在 `~/.claude/settings.json` 注册现有 SessionStart hook（安装器不改 hook 配置）：

```json
{ "hooks": { "SessionStart": [ { "hooks": [ { "type": "command",
  "command": "python3 ~/.claude/skills/my-loop-pm/hooks/inject_decisions.py" } ] } ] } }
```

按需辅助工具 `grilling`、`domain-modeling`、`research`、`diagnosing-bugs` 来自 [mattpocock/skills](https://github.com/mattpocock/skills)，不在此分发包内。使用 Herdr 派工时另需 `herdr`；仅用当前宿主不需要它。

## 验证与来源

```bash
python3 -m unittest discover tests -v
```

回归测试只用标准库，覆盖共享安装、旧副本备份、重复安装、目录别名、决策来源、旧决策兼容、回执文件和状态校验。安装测试在临时目录运行。

上游版本与本地适配的区别见 [SOURCES.md](SOURCES.md)。六套书籍 Skill 是仓库作者整理的工程规则，不是原书全文或原作者官方 Skill。

## 版本与历史证据

- 2026-10-16：接入六套方法论、TasteSkill v2、Wayfinder；落实实现证据与评审核对；合并来源与回执校验修复；统一共享安装和兼容链接。
- v3.2：AGENTS.md 路线与 `review_policy` 协议；PM 直接拆票；收口内置 `my-loop-eli-beginner`。
- v3.1（并入 v3.2）：移除独立文档阶段，Ponytail 的复用顺序并入 worker。
- v3.0：多模型协议与文件交接。
- v2.1（tag）：Claude Code 单会话的四步循环。

`docs/experiments/` 保留早期 L07 实验，`docs/` 中的旧方案和审读记录用于查历史，不代表当前规则。
