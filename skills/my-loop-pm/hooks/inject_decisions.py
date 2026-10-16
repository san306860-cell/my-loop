#!/usr/bin/env python3
"""my-loop v3 · SessionStart hook —— 把已有决策及其来源带入会话

为什么必须是 hook 而不是一句「记得去读决策表」：
指针靠模型自觉，而自觉在上下文变长之后是第一个失效的东西 ——
「新开一个会话，模型不知道为什么这么定，顺手推翻，老 bug 又回来了」
正是这个 hook 要解决的那个痛点本身。

v3 的决策库是 `.my-loop/decisions.jsonl`（一行一条，字段见 assets/schemas/decisions.schema.json）。
老项目的 `.my-loop/DECISIONS.md` 与 `.reins/DECISIONS.md` 继续认 —— 老项目不必迁移。

只注入 status=active 的条目。superseded 的程序过滤，不占上下文。
来源（source）与保护方式（guard）随行注入；来源缺失不代表人类批准。

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

# 超过这个字数就压缩成骨架（id·决策·来源·守卫），保持来源可见：
# 全灌进去等于把最要紧的那几条埋了。
FULL_TEXT_LIMIT = 6000

DIR_NAMES = (".my-loop", ".reins")
COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)

GUARD_LABEL = {"structure": "结构", "test": "测试", "doc": "仅文档", "none": "无"}


def find_stores(start: Path) -> list[tuple[Path, str]]:
    """返回最近一层的候选；空 jsonl 不能遮住同层的旧 Markdown 决策。"""
    for candidate in [start, *start.parents]:
        found: list[tuple[Path, str]] = []
        jsonl = candidate / ".my-loop" / "decisions.jsonl"
        if jsonl.is_file():
            found.append((jsonl, "jsonl"))
        for name in DIR_NAMES:
            md = candidate / name / "DECISIONS.md"
            if md.is_file():
                found.append((md, "md"))
        if found:
            return found
    return []


# ---------- jsonl（v3） ----------

def render_jsonl(path: Path, compact: bool = False) -> str:
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
        if not isinstance(d, dict) or d.get("status") != "active":
            continue
        head = f"{d.get('id', 'D-???')} · {d.get('decision', '').strip()}"
        source = d.get("source")
        source = " ".join(source.split()) if isinstance(source, str) and source.strip() else "未单列；需查原记录，不能推定用户确认"
        parts = [f"来源: {source}"]
        if not compact and d.get("reason"):
            parts.append(f"为什么: {d['reason']}")
        if not compact and d.get("rejected"):
            parts.append(f"否决过: {d['rejected']}")
        parts.append(render_guard(d.get("guard")))
        if d.get("scope"):
            parts.append("域: " + ",".join(d["scope"]))
        blocks.append(head + "\n  " + " ｜ ".join(parts))
    return "\n\n".join(blocks)


def render_guard(guard: dict | None) -> str:
    if not isinstance(guard, dict):
        return "守卫: 未记录"
    gtype = GUARD_LABEL.get(guard.get("type", "none"), "无")
    ref = f" {guard['ref']}" if guard.get("ref") else ""
    return f"守卫: {gtype}{ref}"


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
    keep_prefixes = ("## ", "**决定**", "决定:", "决定：", "**来源**", "来源:", "来源：", "**守卫**", "守卫:", "守卫：", "**不这么做会怎样**")
    return "\n".join(s for line in text.split("\n") if (s := line.strip()).startswith(keep_prefixes))


# ---------- main ----------

def main() -> int:
    try:
        start = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path.cwd()).resolve()
        body = ""
        for path, kind in find_stores(start):
            if kind == "jsonl":
                body = render_jsonl(path)
                if body and len(body) > FULL_TEXT_LIMIT:
                    body = render_jsonl(path, compact=True)
            else:
                body = decisions_only(path.read_text(encoding="utf-8"))
                if body and len(body) > FULL_TEXT_LIMIT:
                    body = condense_md(body)
            if body:
                break
        if not body:
            return 0

        try:
            rel = str(path.relative_to(start))
        except ValueError:
            rel = str(path)

        context = (
            f"以下是这个项目已记录的决策，来自 {rel}；按来源和当前授权适用，不能把所有记录都当作用户批准。\n"
            "给建议、写代码、选方案之前先对一遍：\n"
            "  · 与已决事项一致 → 直接照做，不要重新讨论一遍\n"
            "  · 与已决事项冲突 → 先核对来源和当前明确授权；可逆工程选择在范围内调整，只有尚未决定的目标、关键行为或授权冲突才请用户决定\n"
            "  · 当前明确决定取代旧记录时注明来源；不把未确认假设记录成人已拍板\n"
            "  · 来源未单列的旧记录按来源未知处理，需要时查原记录；不推定用户确认，也不批量要求重新审批\n"
            "  · 「否决过」那一栏是防止你把否决过的方案重新发明出来的\n"
            "  · 只有代码可破坏的行为约束才按实际风险检查结构或测试保护；产品选择、术语和授权记录可以只用文档，不为每条决定补造测试\n"
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
