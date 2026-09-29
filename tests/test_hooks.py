"""hooks 与 install.sh 的回归测试。只用标准库：python3 -m unittest discover tests"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PM = REPO / "skills" / "my-loop-pm"
TEMPLATE = PM / "assets" / "project-template" / ".my-loop"


def run(args: list, **kw) -> subprocess.CompletedProcess:
    return subprocess.run(args, capture_output=True, text=True, **kw)


class Tmp(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.dir, True)


class ValidateState(Tmp):
    def setUp(self) -> None:
        super().setUp()
        shutil.copytree(TEMPLATE, self.dir / ".my-loop")

    def validate(self) -> subprocess.CompletedProcess:
        return run([sys.executable, PM / "hooks" / "validate_state.py", self.dir])

    def test_template_is_valid(self) -> None:
        self.assertEqual(self.validate().returncode, 0)

    def test_state_not_object_is_rejected(self) -> None:
        (self.dir / ".my-loop" / "state.json").write_text("[]")
        r = self.validate()
        self.assertEqual(r.returncode, 1)
        self.assertIn("state.json 顶层必须是对象", r.stdout)

    def test_tickets_not_object_is_rejected_without_crash(self) -> None:
        (self.dir / ".my-loop" / "tickets.json").write_text("[]")
        r = self.validate()
        self.assertEqual(r.returncode, 1)
        self.assertEqual(r.stderr, "")
        self.assertIn("tickets.json 顶层必须是", r.stdout)

    def test_non_object_ticket_and_decision_are_rejected_without_crash(self) -> None:
        (self.dir / ".my-loop" / "tickets.json").write_text('{"tickets": [1]}')
        (self.dir / ".my-loop" / "decisions.jsonl").write_text("[]\n")
        r = self.validate()
        self.assertEqual(r.returncode, 1)
        self.assertEqual(r.stderr, "")


class InjectDecisions(Tmp):
    def inject(self) -> str:
        env = {**os.environ, "CLAUDE_PROJECT_DIR": str(self.dir)}
        return run([sys.executable, PM / "hooks" / "inject_decisions.py"], env=env).stdout

    def test_old_md_still_injected_after_init_copies_empty_jsonl(self) -> None:
        shutil.copytree(TEMPLATE, self.dir / ".my-loop")
        (self.dir / ".my-loop" / "DECISIONS.md").write_text("# 决策\n\n## D-001 用 postgres\n决定: 用 postgres\n")
        out = self.inject()
        self.assertIn("D-001 用 postgres", json.loads(out)["hookSpecificOutput"]["additionalContext"])

    def test_jsonl_wins_when_it_has_active_decisions(self) -> None:
        (self.dir / ".my-loop").mkdir()
        (self.dir / ".my-loop" / "decisions.jsonl").write_text(json.dumps(
            {"id": "D-002", "decision": "用 sqlite", "reason": "r", "status": "active"}, ensure_ascii=False) + "\n")
        (self.dir / ".my-loop" / "DECISIONS.md").write_text("## D-001 用 postgres\n")
        ctx = json.loads(self.inject())["hookSpecificOutput"]["additionalContext"]
        self.assertIn("D-002", ctx)
        self.assertNotIn("D-001", ctx)


class Install(Tmp):
    def test_claude_skills_symlinked_to_shared_dir_stays_intact(self) -> None:
        home = self.dir
        (home / ".agents" / "skills").mkdir(parents=True)
        (home / ".claude").mkdir()
        (home / ".claude" / "skills").symlink_to(home / ".agents" / "skills")
        r = run(["bash", REPO / "install.sh"], env={**os.environ, "HOME": str(home)})
        self.assertEqual(r.returncode, 0, r.stderr)
        skill = home / ".claude" / "skills" / "my-loop-pm" / "SKILL.md"
        self.assertTrue(skill.is_file())
        self.assertFalse((home / ".agents" / "skills" / "my-loop-pm").is_symlink())

    def test_separate_claude_skills_dir_gets_per_skill_links(self) -> None:
        home = self.dir
        (home / ".claude" / "skills").mkdir(parents=True)
        r = run(["bash", REPO / "install.sh"], env={**os.environ, "HOME": str(home)})
        self.assertEqual(r.returncode, 0, r.stderr)
        link = home / ".claude" / "skills" / "my-loop-pm"
        self.assertTrue(link.is_symlink())
        self.assertTrue((link / "SKILL.md").is_file())


if __name__ == "__main__":
    unittest.main()
