# 分发来源与本地适配

本仓库保存所选版本，不在安装时自动追随上游最新分支。升级上游时应单独核对规则变化，并保留其许可证。

| 内容 | 固定来源 | 本地处理 |
|---|---|---|
| Code Complete、A Philosophy of Software Design、Refactoring、Release It!、DDIA、PoEAA | [ciembor/agent-rules-books @ 893a88a](https://github.com/ciembor/agent-rules-books/tree/893a88a6fce3a80c565bf39ac65021b43a8b2990) | 保留各目录的 SKILL、完整规则、mini、nano；各目录附上游 MIT LICENSE |
| Wayfinder | [mattpocock/skills @ 49dd158](https://github.com/mattpocock/skills/tree/49dd158d1076134a641b33efb035946536778336/skills/engineering/wayfinder) | 原版与调用策略保留，附 MIT LICENSE |
| TasteSkill v2 | [Leonxlnx/taste-skill @ f624f37](https://github.com/Leonxlnx/taste-skill/tree/f624f37a8c650b9cc550253104925efe4c8de246/skills/taste-skill) | 正式 v2，安装目录名为 `design-taste-frontend`，原文件保留，附 MIT LICENSE |
| my-loop 四个角色 | 本仓库维护 | 角色分工、验收协议、方法路由、证据核对、脚本与模板 |
| Ponytail | 本地适配版 | 保留明确选择时的 lite/full/ultra；清除与当前工作流冲突的自动触发、最短 diff、固定输出要求 |

方法论原文和 my-loop 如何使用它们分开维护：

- [方法路由](skills/my-loop-pm/references/methodology-routing.md) 定义角色职责、按需使用条件和 Taste 的任务适配；不改写上游规则正文。
- [Wayfinder 适配](skills/my-loop-pm/references/wayfinder.md) 供 PM 在现有 brief 和决策记录中梳理依赖；单独点名 Wayfinder 时仍可使用原版。
- Worker 的 `design_notes` 与 reviewer 的实际核对负责提供应用依据，不要求逐书打卡。

六套书籍规则是 agent-rules-books 作者根据书整理的材料；不是书籍全文，也不代表原书作者官方发布。
