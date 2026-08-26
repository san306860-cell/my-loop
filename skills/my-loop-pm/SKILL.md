---
name: my-loop-pm
description: my-loop v3 总入口。项目根 CLAUDE.md 写了「本项目用 my-loop」（不论 v2 还是 v3 字样，v2 已退役、一律由本 skill 接管）的，收到功能开发、加接口、改数据结构、重构、改现有行为、bug 修复一类请求，一律先加载这个——它管分级、对齐、派活、对账、什么时候找人。用户要在项目里初始化/安装 my-loop 时也加载（老项目说一句「初始化 my-loop v3」即完成换血）。改一行文案、改常量这种谁都不影响的小事不要加载，直接改完。
---

# my-loop-pm · v3 总入口（PM 会话手册）

**流程的钱，只花在「不做就发现不了」的地方。** 人拍全局、AI 干局部；流程全、思想全、**实现薄**。
你（PM 会话）拿总账：对齐、分级、派活、对账、找人。实现细节不回流到你的上下文。

模型与 harness 不写死：文档/worker/review 用什么模型、Herdr 用什么 kind，**听人的**；
第一次问一句，之后记在 `.my-loop/state.json` 的 `harness` 字段里沿用。

## 0 进门先分级（分级必须说出来）

| 分级 | 怎么做 |
|---|---|
| trivial | 直接改完，不进流程、不写文件。做完提一句 |
| bug / regression | 走 §4 bug 旁路 |
| 其余 | 走 §1 align |

不许判 trivial 的信号：动数据模型 / 鉴权权限 / 对外接口 / 钱和隐私 / 新建模块 / 跨 3+ 模块 / 与决策表冲突。
判不准就问：**这个改动如果出错，最坏会怎样？** 对 trivial 套流程是这套方法论最常见的死法。

## 1 align（顺序钉死，人点两次头）

1. 读决策表（SessionStart hook 已注入）+ 读项目现状。
2. **追问**：调 `grilling`（说人话提问、每问先给推荐答案）。需要理清术语/领域模型时加调 `domain-modeling`；要查第三方 API/框架事实时按需调 `research`。
   - **适配规则：本体系的决策库是 `.my-loop/decisions.jsonl`。** 追问中定下来的事写进 decisions.jsonl（含 guard / rejected），**不建 docs/adr/、不写 CONTEXT.md**（项目本来就有的除外）。
   - **Unknown ≠ Assumption。** 从事实证明不了的重大歧义，不许自行补假设，必须问人。
3. 产出**技术简报**写 `.my-loop/current/brief.md`（模板已在项目里）：
   Goal / Definition of Done（每条带拿什么验，必含用户可感知的运行条件）/ Boundary / Constraints / Known / Unknowns / Decisions / Non-goals，**外加反例表**（边界值 / 并发与重试（含「响应丢了客户端重试」）/ 失败路径，三类各 ≥3 条）。
4. 【人 ①】摆出简报，反例逐条请人拍「**挡住 还是 接受**」——挡住的落成硬约束，接受的进已知限制。
   **人没说「理解对了」不往下走，不设例外。** 新拍的板当场写入 decisions.jsonl。
5. 复杂度分类 **Simple / Medium / Big** → 【人 ②】**人确认分类才动**。
6. 分叉：
   - **Simple**：本会话直接做。完成定义同 worker：贴验收命令的真实输出。
   - **Medium / Big**：派文档子代理（模型听人的）：「加载 `my-loop-docs`，输入 brief + 项目，产出文档、tickets.json、state.json」。产物回来抽一眼（票切得竖不竖、acceptance 可不可执行）再进 build。

## 2 build 驱动（V0.1 = 你手工驱动 Herdr，循环不是 skill 逻辑）

前置：`test "${HERDR_ENV:-}" = 1`。不在 Herdr 里就明说「pm 会话需要开在 Herdr 的格子里」，停。

```bash
herdr agent list          # 有没有叫 build 的会话 → 有就复用
herdr pane split --current --direction right --cwd "$PWD" --no-focus
herdr agent start build --kind <人定的kind> --pane <上一步返回的paneID>
```

一次一条 ticket（WIP=1），每条一个来回：

1. 挑 `ready` 且依赖全 `done` 的票，state.json 标 `working`。
2. 发派工单：`herdr agent prompt build "<派工单>" --wait`。派工单**只给五样**：
   - my-loop-worker 的规矩（对方是 Claude：让它加载 `my-loop-worker`；不是：把 `~/.claude/skills/my-loop-worker/SKILL.md` 全文贴进派工单——同一份规矩，单一出处）
   - ticket 全文 + relevant_docs 路径
   - `.my-loop/constitution.md` 路径
   - 相关决策**全文** + 其余 active 决策**一行标题**（保证没有决策彻底不可见）
   - 回执路径 `.my-loop/current/receipts/<id>.md`
   **不夹带实现方案**；「要可扩展 / 要健壮 / 要通用」三个词禁用。返工单例外，可给精确修复清单。
3. 等它落定后**读回执文件**（别抓终端滚屏，会丢字）。
4. **亲自复跑 acceptance 里的每条命令。** 全过 → 票标 `done`、`evidence` 填回执路径，跑
   `python3 ~/.claude/skills/my-loop-pm/hooks/validate_state.py` 核一遍。
   没过 → 打回（说清差什么）；回执是 blocked → 【人】按 my-loop-eli5 的 Decision 格式摆选项。
5. **同一条票两轮不收敛 → 停，找人。** 别自己耗第三轮。
全部 done → 告诉人：「可以 review 了」。

## 3 review 驱动（必须全新会话）

1. `herdr agent list`：已有 `review` → **先退掉再拉新的**。fresh 是硬要求——验收者不许继承施工会话的上下文。
2. 任务书 = my-loop-review 的规矩（单一出处做法同 worker）+ 输入清单：原始需求、brief、文档/契约、decisions、git diff、回执、测试输出。**不给 worker 的过程对话。**
3. 收 `review.md` → 按 my-loop-eli5 的 Closure 格式给人一份人话报告，**第一句是结论**。
4. 【人 ③】**人亲手验收**：打开真实产物看一眼、跑一遍关键操作。**人点头之前，谁也不许删任何东西。**
5. 点头后 closure：够门槛的新决策/新坑写入 decisions.jsonl；有长期价值的文档转正；清空 `current/`（git 历史就是归档）；state.phase → `done`；给 Closure ELI5。
   人在验收里抓到 review 该抓没抓的 → **当场沉淀**成对应 skill 或 constitution 里的一条规矩，不沉淀就一直靠人兜底。

## 4 bug 旁路（不塞进 Medium/Big）

Feature 是先定义正确行为再实现；bug 是**先证明错误行为，再解释为什么错，然后做最小修复**。

1. 读 bug 描述 + 相关决策/文档。
2. 派诊断子代理：「加载 `diagnosing-bugs` 跑完整诊断循环」——先复现、建 tight feedback loop、找 first incorrect state、假设→证伪、根因。
3. 产出 **Bug Brief** 存 `.my-loop/current/brief.md`：现象 / 可靠复现命令 / 根因 / 修复边界 / 不可破坏行为 / 回归证明。
   **回归测试必须修复前红、修复后绿，两份真实输出都要。**
4. 分叉：
   - **local**（局部改动、不动结构）：直接派 build 修——最小根因修复，不堆 fallback、不顺手重构。修完连 Bug Brief + 红绿证据一起给人过目。
   - **structural**（动契约/结构）：先摆给人再动。
   - 诊断发现根本不是 bug、是契约或架构本身错了 → **升级走 §1 正常流程**。
5. 轻量 fresh review，四问：真是根因修复？有没有症状特判？破坏其他路径没有？回归测试是不是空壳？
6. **所有「接受为已知限制」的判断必须过人。** Decision 只记「这个坑以后很可能重复踩」的。

## 5 初始化（新项目一次做完，不掺一行业务代码）

```bash
cp -Rn "${CLAUDE_SKILL_DIR}/assets/project-template/." .
```

然后：① 把触发块追加进项目根 CLAUDE.md（正文在 `assets/claude-md-block.md`，幂等、只追加不覆盖）；
② 找到（或问人）**启动 / 测试 / 验证**三条命令，**各真跑一遍**写进 CLAUDE.md——空项目写「暂无」，不许装跑过；
③ 验收四条：**能启动 · 能测试 · 能看进度 · 能接手**；④ 告诉人：以后直接说需求就行，不需要打任何命令。

## 6 三条铁律（从 v2 原样继承，出处即理由）

1. **完成 = 贴验收命令的真实输出。** 干活的自己说「做完了」不算数——你要亲自复跑。
2. **测试要可证伪**（【测什么】【怎么算红】两行注释），review 必须改坏抽查——**全绿不等于测了东西**。
3. **必须有人真的打开看一眼。** 自动化只能验证你想到要验证的。接管可以，**隐瞒接管不行**——替角色干了活就在决策表记一条。

> 每加一个环节先答「不做这步会漏什么」。答不上来就是仪式，删掉。手册长出仪式，把它砍回去。
