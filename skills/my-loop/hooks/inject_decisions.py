#!/usr/bin/env python3
"""my-loop · SessionStart hook —— 把「已经拍过板的决策」塞进每次会话的开头

为什么必须是 hook 而不是一句「记得去读 DECISIONS.md」：
指针靠模型自觉，而自觉在上下文变长之后是第一个失效的东西 ——
「新开一个会话，模型不知道为什么这么定，顺手推翻，老 bug 又回来了」
正是这个 hook 要解决的那个痛点本身。

**只注入决策表。** 过了三道门槛（难以回退／缺上下文会让人困惑／是真取舍）的那几条。
踩过的坑、纠正过的写法、术语放哪叫什么由项目自己定，一律不注入：
每次会话灌进去只会挤掉真正要紧的几条 —— 注入太多等于没注入。

这是整套 my-loop 里唯一还有脚本参与的地方，留着的理由很窄：
**agent 没法在会话开始之前往自己的上下文里塞东西。** 而它只搬运，不判断。

契约（见 Claude Code hooks 文档）：
    退出码 0 + stdout 上一份 JSON，`hookSpecificOutput.additionalContext` 里的文字模型能看到。
    SessionStart 拦不住会话，所以这里**任何异常都必须吞掉并静默退出** ——
    一个会让会话报错的记忆钩子，第二天就会被人从 settings.json 里删掉。
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

# 超过这个字数就只注入每条决策的标题、结论与守卫。
# 上限不是省钱，是防挤占：把 200 条决策全灌进去，等于把最要紧的那三条埋了。
FULL_TEXT_LIMIT = 6000

# 新路径优先；旧的 .reins/ 仍然认，这样已有项目不必迁移。
DIR_NAMES = (".my-loop", ".reins")

COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)


def find_decisions(start: Path) -> Path | None:
    """从当前目录逐级向上找决策表，新路径优先。"""
    for candidate in [start, *start.parents]:
        for name in DIR_NAMES:
            f = candidate / name / "DECISIONS.md"
            if f.is_file():
                return f
    return None


def decisions_only(text: str) -> str:
    """只抠出 `## D-xxx` 那些段，别的一概不要。

    两样东西必须挡在外面，它们都长得很像内容：

    1. **`<!-- -->` 里的模板示例。** 不剥注释，一个刚装好、一条决策都没有的项目
       会把「## D-001 · 一句话说清决定了什么」当成真决策注入 ——
       模型于是以为这个项目决定过什么事。**空的要显示空，不许编。**
    2. **给人看的说明段（`>` 引言）。** 那是写给读文件的人的规矩，
       每次会话灌一遍纯属挤占 —— 注入的每一个字都在和真正要紧的那几条抢注意力。
    """
    body = COMMENT_RE.sub("", text)
    blocks: list[str] = []
    current: list[str] | None = None
    for line in body.split("\n"):
        if line.startswith("## "):
            if current:
                blocks.append("\n".join(current).rstrip())
            current = [line] if line.startswith("## D-") else None
            continue
        if line.startswith("# "):
            if current:
                blocks.append("\n".join(current).rstrip())
            current = None
            continue
        if current is not None:
            current.append(line)
    if current:
        blocks.append("\n".join(current).rstrip())
    return "\n\n".join(b for b in blocks if b.strip())


def condense(text: str) -> str:
    """太长时只留骨头：标题 + 决定 + 不这么做会怎样 + 守卫。

    「守卫」必须留在骨头里 —— 它标出哪些决策是裸奔的，
    而裸奔的那几条正是最可能被这次会话推翻的。
    """
    keep_prefixes = ("## ", "**决定**", "决定:", "**守卫**", "守卫:", "**不这么做会怎样**")
    kept: list[str] = []
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith(keep_prefixes):
            kept.append(stripped)
    return "\n".join(kept)


def main() -> int:
    try:
        # hook 的 cwd 就是项目目录；再兜一层 CLAUDE_PROJECT_DIR，两个都不在就静默退出
        start = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path.cwd()).resolve()
        decisions = find_decisions(start)
        if decisions is None:
            return 0

        body = decisions_only(decisions.read_text(encoding="utf-8"))
        if not body:
            return 0  # 一条决策都还没有 —— 静默，不许注入一份空模板冒充内容
        if len(body) > FULL_TEXT_LIMIT:
            body = condense(body)

        rel = decisions.name
        try:
            rel = str(decisions.relative_to(start))
        except ValueError:
            rel = str(decisions)

        context = (
            f"以下是这个项目**已经由人拍过板的决策**，来自 {rel}。\n"
            "给建议、写代码、选方案之前先对一遍：\n"
            "  · 与已决事项一致 → 直接照做，不要重新讨论一遍\n"
            "  · 与已决事项冲突 → **停下来告诉人哪一条冲突了，让人裁**，不许自行改写决策\n"
            "  · 看「不这么做会怎样」那一栏 —— 那里写的是代价，不是偏好\n"
            "  · 守卫标着「仅文档」或「无」的条目最脆弱：它们没有测试或结构兜底，\n"
            "    你一旦改动相关代码，没有任何东西会变红来提醒你\n"
            "  · 文档以最新内容为准（人可以手改），你读到的这份就是最新的\n\n"
            f"{body}\n"
        )
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": context,
            }
        }, ensure_ascii=False))
    except Exception:  # noqa: BLE001
        # 记忆钩子不该有能力搞砸一次会话。坏了就当它不存在。
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
