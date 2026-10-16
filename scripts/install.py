#!/usr/bin/env python3
"""Install the bundled skills once, with backed-up per-host compatibility links."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import sys
import tempfile
import uuid

SOURCE = Path(__file__).resolve().parent.parent / "skills"
IGNORED = {"__pycache__", ".DS_Store", ".git", "node_modules"}
RETIRED = ("my-loop-docs", "my-loop-eli5")
# Only add optional host directories when that host already has a local home.
HOST_ROOTS = {
    ".cursor": (".cursor/skills",),
    ".pi": (".pi/agent/skills",),
    ".devin": (".config/devin/skills", ".config/cognition/skills"),
    ".config/devin": (".config/devin/skills",),
    ".config/cognition": (".config/cognition/skills",),
    ".dsh": (".dsh/skills",),
    ".gemini/config": (".gemini/config/skills",),  # agy / Antigravity CLI
    ".kiro": (".kiro/skills",),
    ".workbuddy": (".workbuddy/skills",),
    ".codebuddy": (".codebuddy/skills",),
}
# Old releases copied into these paths. Keep existing entrypoints current, but
# do not create unverified legacy search directories on a new computer.
LEGACY_ROOTS = (".pi/skills", ".devin/skills", ".mirasim/skills")


def ignored(directory: str, names: list[str]) -> list[str]:
    return [name for name in names if name in IGNORED or name.endswith(".pyc")]


def signature(root: Path) -> dict:
    """Compare contents and executable bits; generated caches are irrelevant."""
    result = {}
    for directory, dirs, files in os.walk(root):
        dirs[:] = sorted(name for name in dirs if name not in IGNORED)
        for name in [*dirs, *sorted(files)]:
            if name in ignored(directory, [name]):
                continue
            path = Path(directory) / name
            relative = str(path.relative_to(root))
            if path.is_symlink():
                result[relative] = ("link", os.readlink(path))
            elif path.is_file():
                result[relative] = (
                    "file", hashlib.sha256(path.read_bytes()).hexdigest(),
                    stat.S_IMODE(path.stat().st_mode) & 0o111,
                )
    return result


def host_roots(home: Path, custom_codex_home: str | None = None) -> list[Path]:
    roots = [home / ".codex/skills", home / ".claude/skills"]
    if custom_codex_home:
        roots.append(Path(custom_codex_home).expanduser().absolute() / "skills")
    for marker, paths in HOST_ROOTS.items():
        if (home / marker).is_dir():
            roots.extend(home / path for path in paths)
    roots.extend(home / path for path in LEGACY_ROOTS if (home / path).is_dir())
    return list(dict.fromkeys(roots))


def links_to(target: Path, canonical: Path) -> bool:
    try:
        return target.is_symlink() and target.resolve() == canonical
    except (OSError, RuntimeError):
        # A broken individual link can be backed up and replaced. Root-directory
        # resolution remains strict so an invalid root cannot redirect the batch.
        return False


def plan_install(home: Path, names: list[str], roots: list[Path]) -> list[tuple[str, Path, str]]:
    shared = home / ".agents/skills"
    actions = []
    for name in names:
        target = shared / name
        if target.is_symlink() or not target.is_dir() or signature(target) != signature(SOURCE / name):
            actions.append(("copy", target, name))
    # A whole skills directory may already alias the shared directory. Never
    # replace its children with links to themselves; process each real root once.
    seen = {shared.resolve()}
    active_roots = [shared]
    for root in roots:
        resolved = root.resolve()
        if resolved in seen:
            continue
        if resolved == SOURCE.resolve():
            raise ValueError(f"宿主目录指向仓库源码，不能替换：{root}")
        seen.add(resolved)
        active_roots.append(root)
        for name in names:
            target = root / name
            canonical = shared.resolve() / name
            if not links_to(target, canonical):
                actions.append(("link", target, name))
    for root in active_roots:
        for name in RETIRED:
            target = root / name
            if os.path.lexists(target):
                actions.append(("retire", target, name))
    return actions


def install(actions: list[tuple[str, Path, str]], home: Path) -> Path | None:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_root = home / ".agents/backups/my-loop" / f"{stamp}-{uuid.uuid4().hex[:8]}"
    records = []

    def preserve(target: Path) -> Path | None:
        if not os.path.lexists(target):
            return None
        # Hash the full path so custom host roots cannot collide in the backup.
        key = hashlib.sha256(str(target).encode()).hexdigest()[:16]
        saved = backup_root / key / target.name
        saved.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(target), str(saved))
        record = {"original": str(target), "backup": str(saved)}
        pending = backup_root / ".manifest.tmp"
        try:
            pending.write_text(json.dumps([*records, record], ensure_ascii=False, indent=2) + "\n")
            pending.replace(backup_root / "manifest.json")
        except (OSError, UnicodeError) as exc:
            try:
                shutil.move(str(saved), str(target))
            except OSError as restore_error:
                raise RuntimeError(f"备份记录写入失败且无法恢复 {target}；原内容保留在 {saved}：{restore_error}") from exc
            try:
                pending.unlink(missing_ok=True)
            except OSError:
                pass
            raise OSError(f"备份记录写入失败，已恢复 {target}：{exc}") from exc
        records.append(record)
        return saved

    for kind, target, name in actions:
        target.parent.mkdir(parents=True, exist_ok=True)
        if kind == "retire":
            preserve(target)
            continue
        # Prepare first; a copy error must leave the working installation intact.
        with tempfile.TemporaryDirectory(prefix=".my-loop-install-", dir=target.parent) as stage:
            staged = Path(stage) / name
            if kind == "copy":
                shutil.copytree(SOURCE / name, staged, ignore=ignored)
            else:
                staged.symlink_to(home / ".agents/skills" / name, target_is_directory=True)
            saved = preserve(target)
            try:
                staged.rename(target)
            except OSError as exc:
                if saved is not None:
                    try:
                        shutil.move(str(saved), str(target))
                    except OSError as restore_error:
                        raise RuntimeError(f"安装失败且无法恢复 {target}；原内容保留在 {saved}：{restore_error}") from exc
                raise
    return backup_root if records else None


def main() -> int:
    parser = argparse.ArgumentParser(description="同步共享 Skills，并链接已安装宿主的入口；替换前备份。")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="只列出变更，不写文件")
    mode.add_argument("--check", action="store_true", help="只检查一致性；发现旧版本或缺失链接时返回 1")
    parser.add_argument("--home", type=Path, help="指定独立安装目录，主要用于隔离验证")
    args = parser.parse_args()
    home = (args.home or Path.home()).expanduser().absolute()
    names = sorted(p.name for p in SOURCE.iterdir() if p.is_dir() and (p / "SKILL.md").is_file())
    if not names:
        parser.error("仓库 skills/ 中没有可安装的 Skill")
    roots = host_roots(home, os.environ.get("CODEX_HOME") if args.home is None else None)
    actions = plan_install(home, names, roots)
    for kind, target, _ in actions:
        print(f"{kind:6} {target}")
    if args.dry_run:
        print(f"预览：{len(names)} 个 Skill，{len(actions)} 处变更；未写入。")
        return 0
    if args.check:
        print(f"检查：{len(names)} 个 Skill，{len(roots)} 个兼容入口，{len(actions)} 处不一致。")
        return int(bool(actions))
    backup = install(actions, home)
    if plan_install(home, names, roots):
        raise RuntimeError("安装后的内容或链接仍不一致")
    print(f"已同步 {len(names)} 个 Skill；{len(roots)} 个兼容入口均使用 {home / '.agents/skills'}。")
    if backup:
        print(f"原文件备份：{backup}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"安装失败：{exc}", file=sys.stderr)
        sys.exit(1)
