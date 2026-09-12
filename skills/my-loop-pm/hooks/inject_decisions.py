#!/usr/bin/env python3
"""my-loop v3 · SessionStart hook —— 把「已经拍过板的决策」塞进每次会话的开头

为什么必须是 hook 而不是一句「记得去读决策表」：
指针靠模型自觉，而自觉在上下文变长之后是第一个失效的东西 ——
「新开一个会话，模型不知道为什么这么定，顺手推翻，老 bug 又回来了」
正是这个 hook 要解决的那个痛点本身。

v3 的决策库是 `.my-loop/decisions.jsonl`（一行一条，字段见 assets/schemas/decisions.schema.json）。
还没换血的老项目，`.my-loop/DECISIONS.md` 与 `.reins/DECISIONS.md` 兜底；
一旦 jsonl 出现就只读 jsonl —— 所以换血要用 migrate_v2.py 一次转完，不许两份并存。

只注入 status=active 的条目。superseded 的程序过滤，不占上下文。
守卫（guard）必须随行注入：doc/none 是裸奔条目，恰是最可能被这次会话推翻的。

契约（Claude Code hooks）：退出码 0 + stdout 一份 JSON，
`hookSpecificOutput.additionalContext` 里的文字模型能看到。
SessionStart 拦不住会话，所以**任何异常都必须吞掉并静默退出** ——
一个会让会话报错的记忆钩子，第二天就会被人从 settings.json 里删掉。
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

# 超过这个字数就压缩成骨架（id·决策·守卫）。上限不是省钱，是防挤占：
# 全灌进去等于把最要紧的那几条埋了。
FULL_TEXT_LIMIT = 6000

DIR_NAMES = (".my-loop", ".reins")
COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)

GUARD_LABEL = {"structure": "结构", "test": "测试", "doc": "仅文档", "none": "无"}


def find_store(start: Path) -> tuple[Path, str] | None:
    """从当前目录逐级向上找决策库。新 jsonl 优先，老 md 兜底。"""
    for candidate in [start, *start.parents]:
        jsonl = candidate / ".my-loop" / "decisions.jsonl"
        if jsonl.is_file():
            return jsonl, "jsonl"
        for name in DIR_NAMES:
            md = candidate / name / "DECISIONS.md"
            if md.is_file():
                return md, "md"
    return None


# ---------- jsonl（v3） ----------

def render_jsonl(path: Path) -> str:
    """active 条目渲染成给模型看的块。坏行静默跳过 —— 钩子没资格让会话报错。"""
    blocks: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except Exception:  # noqa: BLE001
            continue
        if d.get("status") != "active":
            continue
        head = f"{d.get('id', 'D-???')} · {d.get('decision', '').strip()}"
        parts: list[str] = []
        if d.get("reason"):
            parts.append(f"为什么: {d['reason']}")
        if d.get("rejected"):
            parts.append(f"否决过: {d['rejected']}")
        parts.append(render_guard(d.get("guard")))
        if d.get("scope"):
            parts.append("域: " + ",".join(d["scope"]))
        blocks.append(head + "\n  " + " ｜ ".join(parts))
    return "\n\n".join(blocks)


def render_guard(guard: dict | None) -> str:
    if not isinstance(guard, dict):
        return "守卫: 无 ⚠裸奔"
    gtype = GUARD_LABEL.get(guard.get("type", "none"), "无")
    ref = f" {guard['ref']}" if guard.get("ref") else ""
    naked = " ⚠裸奔" if guard.get("type") in (None, "doc", "none") else ""
    return f"守卫: {gtype}{ref}{naked}"


def condense_jsonl(text: str) -> str:
    """太长只留骨头：标题行 + 守卫。守卫必须留 —— 裸奔的那几条正是最可能被推翻的。"""
    kept: list[str] = []
    for block in text.split("\n\n"):
        lines = block.split("\n")
        head = lines[0] if lines else ""
        guard = next((p.strip() for p in lines[1].split("｜") if "守卫" in p), "") if len(lines) > 1 else ""
        kept.append(f"{head} ｜ {guard}".rstrip(" ｜"))
    return "\n".join(kept)


# ---------- md（v2 兼容，逻辑原样保留） ----------

def decisions_only(text: str) -> str:
    """只抠 `## D-xxx` 段。模板示例（注释里）和给人看的说明段都挡在外面 ——
    空的要显示空，不许拿模板冒充内容。"""
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


def condense_md(text: str) -> str:
    keep_prefixes = ("## ", "**决定**", "决定:", "**守卫**", "守卫:", "**不这么做会怎样**")
    return "\n".join(s for line in text.split("\n") if (s := line.strip()).startswith(keep_prefixes))


# ---------- main ----------

def main() -> int:
    try:
        start = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path.cwd()).resolve()
        found = find_store(start)
        if found is None:
            return 0
        path, kind = found

        if kind == "jsonl":
            body = render_jsonl(path)
            if not body:
                return 0  # 一条 active 决策都没有 —— 静默，空的要显示空
            if len(body) > FULL_TEXT_LIMIT:
                body = condense_jsonl(body)
        else:
            body = decisions_only(path.read_text(encoding="utf-8"))
            if not body:
                return 0
            if len(body) > FULL_TEXT_LIMIT:
                body = condense_md(body)

        try:
            rel = str(path.relative_to(start))
        except ValueError:
            rel = str(path)

        context = (
            f"以下是这个项目**已经由人拍过板的决策**，来自 {rel}。\n"
            "给建议、写代码、选方案之前先对一遍：\n"
            "  · 与已决事项一致 → 直接照做，不要重新讨论一遍\n"
            "  · 与已决事项冲突 → **停下来告诉人哪一条冲突了，让人裁**，不许自行改写决策\n"
            "  · 「否决过」那一栏是防止你把否决过的方案重新发明出来的\n"
            "  · 守卫标着「仅文档」或「无」（⚠裸奔）的条目最脆弱：没有测试或结构兜底，\n"
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
