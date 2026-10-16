"""Public installer behavior, using independent temporary homes."""

import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

REPO = Path(__file__).resolve().parent.parent


class Installation(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name).resolve()

    def install(self, *args):
        return subprocess.run(
            ["bash", str(REPO / "install.sh"), "--home", str(self.home), *args],
            capture_output=True, text=True,
        )

    def test_preview_and_check_do_not_write(self):
        (self.home / ".cursor").mkdir()
        before = sorted(str(p) for p in self.home.rglob("*"))
        self.assertEqual(self.install("--dry-run").returncode, 0)
        self.assertEqual(self.install("--check").returncode, 1)
        self.assertEqual(before, sorted(str(p) for p in self.home.rglob("*")))

    def test_install_dependencies_to_real_host_paths_and_is_idempotent(self):
        for host in (".pi", ".devin", ".cursor", ".dsh", ".kiro", ".workbuddy", ".gemini/config"):
            (self.home / host).mkdir(parents=True)
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stderr)
        names = ("my-loop-pm", "my-loop-worker", "my-loop-review", "code-complete",
                 "a-philosophy-of-software-design", "refactoring", "release-it",
                 "designing-data-intensive-applications", "patterns-of-enterprise-application-architecture",
                 "design-taste-frontend", "wayfinder", "ponytail", "my-loop-eli-beginner")
        for root in (".codex/skills", ".claude/skills", ".pi/agent/skills", ".config/devin/skills",
                     ".config/cognition/skills", ".cursor/skills", ".dsh/skills", ".kiro/skills",
                     ".workbuddy/skills", ".gemini/config/skills"):
            for name in names:
                with self.subTest(root=root, name=name):
                    link = self.home / root / name
                    self.assertTrue(link.is_symlink())
                    self.assertEqual(link.resolve(), self.home / ".agents/skills" / name)
                    self.assertTrue((link / "SKILL.md").is_file())
        self.assertFalse((self.home / ".pi/skills").exists())
        self.assertFalse((self.home / ".devin/skills").exists())
        self.assertFalse((self.home / ".gemini/skills").exists())
        self.assertEqual(self.install("--check").returncode, 0)
        self.assertEqual(self.install().returncode, 0)
        self.assertFalse((self.home / ".agents/backups").exists())

    def test_stale_copies_and_retired_skills_are_backed_up(self):
        stale = self.home / ".cursor/skills/my-loop-pm"
        stale.mkdir(parents=True)
        (stale / "SKILL.md").write_text("locally edited old version")
        retired = self.home / ".pi/skills/my-loop-eli5"
        retired.mkdir(parents=True)
        (retired / "SKILL.md").write_text("retired original")
        unrelated = self.home / ".cursor/skills/other-skill/SKILL.md"
        unrelated.parent.mkdir()
        unrelated.write_text("leave this unchanged")
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(stale.is_symlink())
        self.assertFalse(retired.exists())
        self.assertEqual(unrelated.read_text(), "leave this unchanged")
        records = json.loads(next((self.home / ".agents/backups/my-loop").glob("*/manifest.json")).read_text())
        saved = {entry["original"]: Path(entry["backup"]) for entry in records}
        self.assertEqual((saved[str(stale)] / "SKILL.md").read_text(), "locally edited old version")
        self.assertEqual((saved[str(retired)] / "SKILL.md").read_text(), "retired original")
        self.assertEqual(self.install("--check").returncode, 0)

    def test_repair_canonical_and_host_links_without_touching_external_original(self):
        old = self.home / "external-original"
        old.mkdir()
        (old / "SKILL.md").write_text("external original")
        canonical = self.home / ".agents/skills/my-loop-pm"
        canonical.parent.mkdir(parents=True)
        canonical.symlink_to(old)
        host = self.home / ".codex/skills/my-loop-pm"
        host.parent.mkdir(parents=True)
        host.symlink_to(old)
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(canonical.is_symlink())
        self.assertEqual(host.resolve(), canonical)
        self.assertEqual((old / "SKILL.md").read_text(), "external original")

    def test_check_detects_content_drift_and_broken_link(self):
        self.assertEqual(self.install().returncode, 0)
        source = self.home / ".agents/skills/my-loop-worker/SKILL.md"
        source.write_text("stale")
        host = self.home / ".claude/skills/wayfinder"
        host.unlink()
        host.symlink_to(self.home / "missing-wayfinder")
        self.assertEqual(self.install("--check").returncode, 1)
        self.assertEqual(self.install().returncode, 0)
        self.assertEqual(self.install("--check").returncode, 0)
        self.assertEqual(source.read_bytes(), (REPO / "skills/my-loop-worker/SKILL.md").read_bytes())

    def test_cyclic_individual_skill_links_are_repaired(self):
        for canonical_loop in (False, True):
            with self.subTest(canonical_loop=canonical_loop):
                self.home = Path(self.temp.name).resolve() / str(canonical_loop)
                canonical = self.home / ".agents/skills/my-loop-pm"
                host = self.home / ".codex/skills/my-loop-pm"
                host.parent.mkdir(parents=True)
                if canonical_loop:
                    canonical.parent.mkdir(parents=True)
                    canonical.symlink_to(canonical)
                    host.symlink_to(canonical)
                else:
                    host.symlink_to(host)
                result = self.install()
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertFalse(canonical.is_symlink())
                self.assertEqual(host.resolve(), canonical)
                self.assertTrue((host / "SKILL.md").is_file())

    def test_backup_record_failure_restores_original_before_exiting(self):
        spec = importlib.util.spec_from_file_location("my_loop_installer", REPO / "scripts/install.py")
        installer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(installer)
        real_write = Path.write_text

        def fail_manifest(path, *args, **kwargs):
            if path.name == ".manifest.tmp":
                raise OSError("injected manifest write failure")
            return real_write(path, *args, **kwargs)

        for kind in ("copy", "link", "retire"):
            with self.subTest(kind=kind):
                home = self.home / kind
                target = home / ".agents/skills/my-loop-pm"
                target.mkdir(parents=True)
                (target / "SKILL.md").write_text("original must survive")
                with mock.patch.object(Path, "write_text", fail_manifest):
                    with self.assertRaisesRegex(OSError, "已恢复"):
                        installer.install([(kind, target, "my-loop-pm")], home)
                self.assertEqual((target / "SKILL.md").read_text(), "original must survive")
                self.assertFalse(target.is_symlink())


if __name__ == "__main__":
    unittest.main()
