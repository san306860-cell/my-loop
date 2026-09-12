#!/usr/bin/env python3
"""my-loop v3 · 老项目换血 —— 把 v2 的 DECISIONS.md 转进 decisions.jsonl，然后删掉 md

为什么要一次转完：inject_decisions.py 一旦看见 jsonl 就不再读 md。
半迁移（新决策写 jsonl、老决策留 md）= 老决策全部对会话隐身，撞上就会被顺手推翻。

v2 条目长这样（一条一段）：

    ## D-001 · 一句话决策 [—— 已被 D-0XX 取代]
    2026-08-19 · 守卫: 仅文档（HANDOFF §4）
    正文（别做什么 · 为什么）……

转出来：decision=标题，reason=正文，guard 按「仅文档/结构/测试/无」映射，
标题里写了「已被 D-0XX 取代」（不含「部分」）的标 superseded。
jsonl 里已有的 id 跳过（jsonl 为准），其余追加到文件末尾。

只用标准库。用法：
    python3 migrate_v2.py [项目目录]     # 缺省从当前目录向上找 .my-loop/ 或 .reins/
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

DIR_NAMES = (".my-loop", ".reins")  # 与 inject_decisions.py 同一优先级

HEAD_RE = re.compile(r"^## (D-\d{3,})\s*[·•]\s*(.*)$")
SUPERSEDED_RE = re.compile(r"已被\s*(D-\d{3,})\s*取代")
GUARD_LINE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})?\s*[·•]?\s*守卫\s*[:：]\s*(.*)$")
GUARD_TYPES = (("仅文档", "doc"), ("结构", "structure"), ("测试", "test"), ("无", "none"))
COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)


def find_md(start: Path) -> Path | None:
    """逐层向上找第一份真存在的 DECISIONS.md（与 inject_decisions.find_store 同一走法）。"""
    for candidate in [start, *start.parents]:
        for name in DIR_NAMES:
            md = candidate / name / "DECISIONS.md"
            if md.is_file():
                return md
        if (candidate / ".my-loop" / "decisions.jsonl").is_file():
            return None  # 这一层已是纯 v3 项目，别越界去迁祖先
    return None


def parse_guard(rest: str) -> dict:
    rest = rest.strip()
    for label, gtype in GUARD_TYPES:
        if rest.startswith(label):
            ref = rest[len(label):].strip(" ：:（）()")
            return {"type": gtype, "ref": ref} if ref else {"type": gtype}
    return {"type": "none", "ref": rest} if rest else {"type": "none"}


def parse_md(text: str) -> list[dict]:
    entries: list[dict] = []
    current: dict | None = None
    body: list[str] = []

    def flush() -> None:
        if current is None:
            return
        current["reason"] = "\n".join(body).strip() or current["decision"]
        entries.append(current)

    for line in COMMENT_RE.sub("", text).split("\n"):
        m = HEAD_RE.match(line)
        if m:
            flush()
            title = m.group(2).strip()
            sup = SUPERSEDED_RE.search(title)
            superseded = bool(sup) and "部分取代" not in title
            current = {
                "id": m.group(1),
                "date": "",
                "decision": title,
                "reason": "",
                "guard": {"type": "none"},
                "status": "superseded" if superseded else "active",
                "superseded_by": sup.group(1) if superseded else None,
            }
            body = []
            continue
        if line.startswith("# "):
            flush()
            current = None
            continue
        if current is None:
            continue
        g = GUARD_LINE_RE.match(line.strip())
        if g and not current["date"] and not body:
            current["date"] = g.group(1) or ""
            current["guard"] = parse_guard(g.group(2))
            continue
        body.append(line)
    flush()
    for e in entries:
        if not e["date"]:
            del e["date"]
    return entries


def main() -> int:
    start = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
    md = find_md(start)
    if md is None:
        print(f"✓ 从 {start} 向上没有 DECISIONS.md，无需迁移")
        return 0
    project = md.parent.parent
    jsonl = project / ".my-loop" / "decisions.jsonl"

    old_lines: list[str] = []
    existing: set[str] = set()
    if jsonl.is_file():
        for line in jsonl.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                existing.add(json.loads(line)["id"])
            except (json.JSONDecodeError, KeyError, TypeError):
                print(f"✗ {jsonl} 里有解不开的行，先修好再迁：{line[:80]}")
                return 1
            old_lines.append(line)

    entries = parse_md(md.read_text(encoding="utf-8"))
    if not entries:
        print(f"✗ {md} 里没解析出任何 `## D-xxx` 条目，没动任何文件")
        return 1
    new = [e for e in entries if e["id"] not in existing]
    skipped = len(entries) - len(new)

    # 全量写临时文件再原子替换：hook 只凭 jsonl 存在与否选数据源，半成品一旦落盘就会把没写完的决策藏起来
    jsonl.parent.mkdir(parents=True, exist_ok=True)
    tmp = jsonl.with_name(jsonl.name + ".tmp")
    all_lines = old_lines + [json.dumps(e, ensure_ascii=False) for e in new]
    with tmp.open("w", encoding="utf-8") as f:
        f.write("\n".join(all_lines) + "\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, jsonl)
    md.unlink()

    print(f"✓ 转入 {len(new)} 条（跳过 jsonl 已有的 {skipped} 条），已删除 {md.relative_to(project)}")
    print("  接着跑 validate_state.py 核一遍；守卫标 doc/none 的老条目会被提醒裸奔，那是事实不是错误")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
