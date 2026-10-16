# my-loop 的六套方法论与可选工具

六套书籍规则来自 [agent-rules-books](https://github.com/ciembor/agent-rules-books)，是作者整理的工程指导。使用项目事实判断适用性，用户明确指令与既有授权优先；书中的强制措辞不自动产生新需求、审批或测试配额。

下面的相对路径从本文件出发，解析到共享 Skills 的真实目录。跨宿主或派工时传可读取的绝对路径；没有 Skill 调用工具时直接打开文件，不声称调用了不存在的工具。

## 常驻分工

| 角色 | 固定资料 | 必须落实的事情 |
|---|---|---|
| Worker，包括 PM 兼任实现者 | [Code Complete mini](../../code-complete/code-complete.mini.md) | 数据含义、控制流与错误处理清楚，边界正确，修改能验证 |
| Worker，包括 PM 兼任实现者 | [A Philosophy of Software Design mini](../../a-philosophy-of-software-design/a-philosophy-of-software-design.mini.md) | 按总复杂度决定边界，让接口隐藏复杂性，减少调用者负担 |
| Reviewer | [Refactoring mini](../../refactoring/refactoring.mini.md) | 识别真实结构障碍，区分行为变化与重构，给小步、有证据的建议 |

实际加载要求分别由 `my-loop-worker`、`my-loop-review` 负责。PM 不能在派工时取消，是否创建子 Agent 不影响这些角色责任。

## 设计阶段按问题启用

| 方法 | 何时读 | 要解决的问题 |
|---|---|---|
| [Release It! mini](../../release-it/release-it.mini.md) | 涉及外部调用、任务队列、长任务、资源池、过载、恢复或部署行为 | 超时后发生什么，何时可以重试，资源如何有界，故障如何隔离、发现与恢复 |
| [DDIA mini](../../designing-data-intensive-applications/designing-data-intensive-applications.mini.md) | 涉及多处写入、缓存/派生数据、并发更新、重复消息、数据迁移或一致性 | 谁拥有真实状态，何时算成功，重复/乱序/旧写如何处理，原子性与兼容边界在哪里 |
| [PoEAA mini](../../patterns-of-enterprise-application-architecture/patterns-of-enterprise-application-architecture.mini.md) | 业务流程、持久化、事务、锁或外部系统边界确实需要设计 | 哪处协调用例、哪处拥有规则与事务，数据库/供应商细节由谁隐藏 |

先理解具体数据流与失败场景，再选择可同时启用的资料。Release It! 在设计时使用，不等发布前才补。简单业务可继续使用直接的用例流程；PoEAA 不意味着必须建 Service、Repository、Mapper 全套层。只有真实边界收益才能支持新增结构。

在现有 brief 的 Constraints / Decisions 中写明「什么问题 → 哪个方法的哪条原则 → 本次约束或选择 → 如何验证」，并给资料链接。同一风险涉及多种方法时共用一条约束和证据；小任务一句即可，不按书分报告。只把与本票有关的链接和本地适配放进 `relevant_docs`，有业务影响的检查进入 acceptance；不要添加方法论打卡字段或专用 ticket。

Worker 在现有回执中用代码位置和依据说明实际选择，Reviewer 沿产物核对关键主张；具体要求由各自 Skill 维护，加载记录不作为应用证明。实施中出现新事实时，在授权内调整可逆细节；改变目标、关键行为或契约的未决事项交 PM 处理。模式名称和未选中的清单不自动成为阻断发现。

## 可选的网页视觉工具

[TasteSkill v2 / design-taste-frontend](../../design-taste-frontend/SKILL.md) 用于官网、落地页、作品页、产品宣传页或相应区块的视觉与交互工作。先看现有品牌、内容、行为和项目设计体系，再按需加载；不因为项目使用 React 就启用，也不默认用于后台、数据表格、编辑器或 Canvas 产品界面。

它提供设计方向、素材参考和浏览器检查。任务采用时，把视觉目标、保留行为、相关视口与交互检查放进现有 brief / acceptance，验收须看真实截图与交互，工具评分不能代表用户审美认可。上游的图片数量、动效数量和个人审美阈值不是 my-loop 的通用 DoD；与明确需求、品牌、无障碍或性能目标冲突时，以任务约束为准并说明例外，不为凑指标扩张页面内容。

启用 Taste 时将上面的适配一并交给 worker/reviewer；工具发现按本任务验收判断，明确不适用的数量或风格项可记录理由，不为了清零工具分数违背任务约束。

当前使用 2026-10-13 发布的正式 v2；旧 `v2-experimental` 是另一个保留版本。按需调用脚本，先核对本地运行条件；执行不了就记录具体未验项，不伪造浏览器检查。

## PM 的决策梳理工具

任务存在互相依赖、暂不能可靠拆施工票的关键未知时，读取 [Wayfinder 的 my-loop 适配](wayfinder.md)。它帮助厘清决定，结果仍交回现有实现与验收流程。
