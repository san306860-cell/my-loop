#!/usr/bin/env python3
"""my-loop v3 · 状态校验器 —— state.json / tickets.json / decisions.jsonl 的机器守门员

「机器只接受明确状态」在 V0.1 没有常驻 controller，靠的就是这只手：
pm 每次改完状态跑一遍，红了就修到绿再往下走。

只用标准库。错误说人话。exit 0 = 全部合法；exit 1 = 有错。⚠ 开头的是提醒，不拦。

用法：
    python3 validate_state.py [项目目录]     # 缺省从当前目录向上找 .my-loop/
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

PHASES = {"idle", "align", "build", "review", "awaiting_acceptance", "done"}
CLASSIFICATIONS = {"simple", "medium", "big", "bug", None}
TICKET_STATUS = {"todo", "ready", "working", "done", "blocked"}
GUARD_TYPES = {"structure", "test", "doc", "none"}
TICKET_ID = re.compile(r"^T-\d{3,}$")
DECISION_ID = re.compile(r"^D-\d{3,}$")


def find_root(start: Path) -> Path | None:
    for candidate in [start, *start.parents]:
        if (candidate / ".my-loop").is_dir():
            return candidate / ".my-loop"
    return None


def load_json(path: Path, errors: list[str]):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        errors.append(f"✗ 缺文件：{path.name}")
    except Exception as e:  # noqa: BLE001
        errors.append(f"✗ {path.name} 不是合法 JSON：{e}")
    return None


def check_state(state: dict, tickets_by_id: dict, errors: list[str], warns: list[str]) -> None:
    if state.get("phase") not in PHASES:
        errors.append(f"✗ state.phase「{state.get('phase')}」不在合法值里：{sorted(PHASES)}")
    if state.get("classification") not in CLASSIFICATIONS:
        errors.append(f"✗ state.classification「{state.get('classification')}」不合法")
    cur = state.get("current_ticket")
    if cur is not None:
        t = tickets_by_id.get(cur)
        if t is None:
            errors.append(f"✗ state.current_ticket 指向不存在的票 {cur}")
        elif t.get("status") != "working":
            errors.append(f"✗ state.current_ticket={cur}，但那张票的状态是「{t.get('status')}」不是 working")


def check_tickets(tickets: list, errors: list[str], warns: list[str]) -> dict:
    by_id: dict[str, dict] = {}
    working = []
    for t in tickets:
        tid = t.get("id", "?")
        if not TICKET_ID.match(str(tid)):
            errors.append(f"✗ 票号「{tid}」不符合 T-001 形式")
        if tid in by_id:
            errors.append(f"✗ 票号 {tid} 重复")
        by_id[str(tid)] = t
        if t.get("status") not in TICKET_STATUS:
            errors.append(f"✗ {tid} 状态「{t.get('status')}」不在合法值里：{sorted(TICKET_STATUS)}")
        acc = t.get("acceptance")
        if not isinstance(acc, list) or not acc or not all(isinstance(a, str) and a.strip() for a in acc):
            errors.append(f"✗ {tid} 的 acceptance 为空——验收命令是票的一部分，没有就不算票")
        if t.get("status") == "working":
            working.append(tid)
        if t.get("status") == "done" and not t.get("evidence"):
            errors.append(f"✗ {tid} 标了 done 但没有 evidence——完成必须贴回执，没证据不算完成")
        if t.get("status") == "blocked" and not t.get("blocked_reason"):
            warns.append(f"⚠ {tid} 标了 blocked 但没写 blocked_reason，人没法拍板")
    if len(working) > 1:
        errors.append(f"✗ 同时有 {len(working)} 张票在 working（{', '.join(working)}）——WIP=1，同一时刻只许一条")
    # 依赖检查
    for t in tickets:
        tid = str(t.get("id"))
        for dep in t.get("depends_on", []) or []:
            if dep not in by_id:
                errors.append(f"✗ {tid} 依赖不存在的票 {dep}")
            elif t.get("status") in ("working", "done") and by_id[dep].get("status") != "done":
                errors.append(f"✗ {tid} 已是 {t.get('status')}，但它依赖的 {dep} 还是「{by_id[dep].get('status')}」——依赖没完成不许开工")
    # 环检测
    state = {}
    def visit(tid: str, stack: list[str]) -> None:
        if state.get(tid) == 2:
            return
        if state.get(tid) == 1:
            errors.append(f"✗ 依赖成环：{' → '.join(stack + [tid])}")
            return
        state[tid] = 1
        for dep in (by_id.get(tid, {}).get("depends_on") or []):
            if dep in by_id:
                visit(dep, stack + [tid])
        state[tid] = 2
    for tid in by_id:
        visit(tid, [])
    return by_id


def check_decisions(path: Path, errors: list[str], warns: list[str]) -> None:
    if not path.is_file():
        return
    ids: set[str] = set()
    entries: list[dict] = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            d = json.loads(line)
        except Exception as e:  # noqa: BLE001
            errors.append(f"✗ decisions.jsonl 第 {i} 行不是合法 JSON：{e}")
            continue
        entries.append(d)
        for field in ("id", "decision", "reason", "status"):
            if not d.get(field):
                errors.append(f"✗ decisions.jsonl 第 {i} 行缺必填字段「{field}」")
        did = str(d.get("id", ""))
        if did and not DECISION_ID.match(did):
            errors.append(f"✗ 决策号「{did}」不符合 D-001 形式")
        if did in ids:
            errors.append(f"✗ 决策号 {did} 重复")
        ids.add(did)
        if d.get("status") not in ("active", "superseded", None):
            errors.append(f"✗ {did} 的 status「{d.get('status')}」不合法（active/superseded）")
        g = d.get("guard")
        if g is not None and (not isinstance(g, dict) or g.get("type") not in GUARD_TYPES):
            errors.append(f"✗ {did} 的 guard 不合法（type 必须是 structure/test/doc/none）")
        elif d.get("status") == "active" and (g is None or g.get("type") in ("doc", "none")):
            warns.append(f"⚠ {did} 守卫裸奔（仅文档/无）——能不能补一条会红的测试？")
    for d in entries:
        sb = d.get("superseded_by")
        if sb and sb not in ids:
            warns.append(f"⚠ {d.get('id')} 标了被 {sb} 取代，但没找到那条")
        if d.get("status") == "superseded" and not sb:
            warns.append(f"⚠ {d.get('id')} 是 superseded 却没写 superseded_by")


def main() -> int:
    start = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
    root = find_root(start)
    if root is None:
        print(f"✗ 从 {start} 向上没找到 .my-loop/ 目录")
        return 1

    errors: list[str] = []
    warns: list[str] = []

    tickets_doc = load_json(root / "tickets.json", errors)
    tickets = tickets_doc.get("tickets", []) if isinstance(tickets_doc, dict) else []
    if tickets_doc is not None and not isinstance(tickets_doc.get("tickets"), list):
        errors.append("✗ tickets.json 顶层必须是 {\"tickets\": [...]}")
    by_id = check_tickets(tickets, errors, warns)

    state = load_json(root / "state.json", errors)
    if isinstance(state, dict):
        check_state(state, by_id, errors, warns)

    check_decisions(root / "decisions.jsonl", errors, warns)

    for w in warns:
        print(w)
    if errors:
        for e in errors:
            print(e)
        print(f"\n{len(errors)} 处不合法。修到全绿再往下走。")
        return 1
    print("✓ state / tickets / decisions 全部合法")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
